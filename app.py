from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import re
import time
import uuid
import requests
import json
import os
from datetime import datetime
from contextlib import contextmanager
from difflib import SequenceMatcher

# ============================================
# د Flask اپلیکیشن ترتیب
# ============================================

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = 'hia-ai-super-secret-key-2024'
CORS(app)

# ============================================
# د API کیلي - دلته خپل کیلي واچوئ
# ============================================

OPENAI_API_KEY = "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"  # خپل OpenAI کیلي دلته واچوئ
QWEN_API_KEY = "sk-ws-H.IIHRDH.6uLt.MEQCIC-ViC9xEY_Ik2OvMBchotiWH3a0q2i-aWYF1I0eKqwnAiABFO5EXiQIsiW9KN2sVvQFlvWQlolK4z0cb7CQ05DYTw"     # خپل Qwen کیلي دلته واچوئ

# ============================================
# د ډیټابیس مدیر (Database Manager)
# ============================================

class DatabaseManager:
    def __init__(self):
        self.db_path = 'hia_ai.db'
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def init_database(self):
        with self.get_connection() as conn:
            # د پوهې جدول
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT UNIQUE,
                    answer TEXT,
                    ai_provider TEXT,
                    keywords TEXT,
                    usage_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # د خبرو اترو جدول
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_question TEXT,
                    ai_answer TEXT,
                    ai_provider TEXT,
                    response_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # د لاګ جدول
            conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_type TEXT,
                    message TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # د احصایې جدول
            conn.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value INTEGER,
                    date DATE DEFAULT CURRENT_DATE
                )
            ''')
    
    def save_knowledge(self, question, answer, provider, keywords):
        with self.get_connection() as conn:
            existing = conn.execute(
                'SELECT id, usage_count FROM knowledge WHERE question = ?', 
                (question,)
            ).fetchone()
            
            if existing:
                conn.execute('''
                    UPDATE knowledge 
                    SET answer = ?, ai_provider = ?, keywords = ?, 
                        usage_count = ?, updated_at = ? 
                    WHERE question = ?
                ''', (answer, provider, keywords, existing['usage_count'] + 1, datetime.now(), question))
            else:
                conn.execute('''
                    INSERT INTO knowledge (question, answer, ai_provider, keywords) 
                    VALUES (?, ?, ?, ?)
                ''', (question, answer, provider, keywords))
    
    def get_knowledge(self, question):
        with self.get_connection() as conn:
            return conn.execute(
                'SELECT * FROM knowledge WHERE question = ?', 
                (question,)
            ).fetchone()
    
    def search_similar(self, keywords, limit=5):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT * FROM knowledge 
                WHERE keywords LIKE ? 
                ORDER BY usage_count DESC, created_at DESC 
                LIMIT ?
            ''', (f'%{keywords}%', limit)).fetchall()
    
    def get_all_knowledge(self, limit=100):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT question, answer, ai_provider, usage_count, created_at 
                FROM knowledge 
                ORDER BY usage_count DESC, created_at DESC 
                LIMIT ?
            ''', (limit,)).fetchall()
    
    def save_conversation(self, session_id, question, answer, provider, response_time):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO conversations (session_id, user_question, ai_answer, ai_provider, response_time) 
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, question, answer, provider, response_time))
    
    def get_conversation_history(self, session_id, limit=50):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT user_question, ai_answer, ai_provider, created_at 
                FROM conversations 
                WHERE session_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (session_id, limit)).fetchall()
    
    def get_statistics(self):
        with self.get_connection() as conn:
            knowledge_count = conn.execute('SELECT COUNT(*) as count FROM knowledge').fetchone()['count']
            conv_count = conn.execute('SELECT COUNT(*) as count FROM conversations').fetchone()['count']
            
            return {
                'total_knowledge': knowledge_count,
                'total_conversations': conv_count,
                'memory_usage': f"{knowledge_count * 0.5:.1f} KB"
            }
    
    def add_log(self, log_type, message, details=None):
        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO logs (log_type, message, details) VALUES (?, ?, ?)',
                (log_type, message, details)
            )

# ============================================
# د AI چمتو کونکي (AI Providers)
# ============================================

class OpenAIProvider:
    def __init__(self, api_key):
        self.api_key = api_key
        self.name = "OpenAI"
    
    def generate(self, prompt):
        try:
            if not self.api_key or self.api_key == "":
                return None
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are HIA AI, an intelligent, friendly, and professional assistant. You support Pashto, Dari, and English."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            response = requests.post(
                "https://api.openai.com/v1/chat/completions", 
                headers=headers, 
                json=data, 
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            return None
        except Exception as e:
            return None

class QwenProvider:
    def __init__(self, api_key):
        self.api_key = api_key
        self.name = "Qwen"
    
    def generate(self, prompt):
        try:
            if not self.api_key or self.api_key == "":
                return None
                
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "qwen-turbo",
                "messages": [
                    {"role": "system", "content": "You are HIA AI."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            response = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", 
                headers=headers, 
                json=data, 
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            return None
        except Exception as e:
            return None

class HIAIntelligentProvider:
    def __init__(self):
        self.name = "HIA Intelligent"
        self.knowledge_base = {
            "سلام": "سلام! زه HIA AI یم. تاسو سره څنګه مرسته کولی شم؟",
            "سلام عليكم": "وعلیکم السلام! ښه راغلاست. زه دلته یم چې ستاسو سره مرسته وکړم.",
            "who are you": "I am HIA AI - an intelligent assistant with memory. I learn from our conversations!",
            "what is ai": "AI (Artificial Intelligence) is the simulation of human intelligence in machines.",
            "what is artificial intelligence": "Artificial Intelligence is the field of computer science focused on creating intelligent machines.",
            "how are you": "I'm functioning perfectly! Ready to help you anytime.",
            "thank you": "You're most welcome! Feel free to ask anything.",
            "bye": "Goodbye! Have a great day!",
            "help": "I can answer questions, remember our conversations, and learn over time. Just ask me anything!",
            "مانیا": "زه HIA AI یم، یو هوښیار مرستیال چې حافظه لري.",
            "څنګه یې": "زه ښه یم، مننه! تاسو څنګه یاست؟"
        }
    
    def generate(self, prompt):
        prompt_lower = prompt.lower().strip()
        
        for key, value in self.knowledge_base.items():
            if key.lower() in prompt_lower:
                return value
        
        return """🤖 **HIA AI Here!**

I understand your question. As an intelligent assistant with memory, I've saved this conversation to learn and provide better answers in the future.

💡 *This interaction has been stored in my knowledge base.*

Ask me anything in Pashto, Dari, or English!"""

# ============================================
# د AI مرکزي روټر (Main AI Router)
# ============================================

class HIAAssistant:
    def __init__(self):
        self.db = DatabaseManager()
        self.providers = []
        self.setup_providers()
    
    def setup_providers(self):
        if OPENAI_API_KEY and OPENAI_API_KEY != "":
            self.providers.append(OpenAIProvider(OPENAI_API_KEY))
        if QWEN_API_KEY and QWEN_API_KEY != "":
            self.providers.append(QwenProvider(QWEN_API_KEY))
        self.providers.append(HIAIntelligentProvider())
    
    def extract_keywords(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'what', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'of', 'to', 'for', 'in', 'on', 'at', 'with', 'by'}
        keywords = ' '.join([w for w in words if w not in stopwords][:10])
        return keywords if keywords else text[:50]
    
    def calculate_similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def check_memory(self, question):
        # دقیق پوښتنه وګوره
        exact_match = self.db.get_knowledge(question)
        if exact_match:
            return {'found': True, 'answer': exact_match['answer'], 'provider': exact_match['ai_provider']}
        
        # ورته پوښتنې وګوره
        keywords = self.extract_keywords(question)
        similar_questions = self.db.search_similar(keywords, 3)
        
        for item in similar_questions:
            similarity = self.calculate_similarity(question, item['question'])
            if similarity > 0.7:
                return {'found': True, 'answer': item['answer'], 'provider': item['ai_provider']}
        
        return {'found': False}
    
    def get_response(self, question, session_id):
        start_time = time.time()
        self.db.add_log('info', f'New question: {question[:50]}')
        
        # لومړی: حافظه وګوره
        memory = self.check_memory(question)
        if memory['found']:
            response_time = time.time() - start_time
            self.db.save_conversation(session_id, question, memory['answer'], memory['provider'], response_time)
            self.db.add_log('memory_hit', f'Answer from memory: {question[:50]}')
            return memory['answer']
        
        # دوهم: AI چمتو کونکي وکاروه
        for provider in self.providers:
            try:
                response = provider.generate(question)
                if response:
                    keywords = self.extract_keywords(question)
                    self.db.save_knowledge(question, response, provider.name, keywords)
                    response_time = time.time() - start_time
                    self.db.save_conversation(session_id, question, response, provider.name, response_time)
                    self.db.add_log('ai_generated', f'Response from {provider.name}')
                    return response
            except Exception as e:
                continue
        
        # دریم: تېروتنه
        error_msg = "I'm having trouble connecting. Please try again in a moment."
        self.db.add_log('error', 'All providers failed')
        return error_msg

# ============================================
# د HIA AI مرکزي انسټنس
# ============================================

hia = HIAAssistant()

# ============================================
# د API لارې (API Routes)
# ============================================

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        answer = hia.get_response(question, session_id)
        
        return jsonify({
            'answer': answer,
            'session_id': session_id,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    history = hia.db.get_conversation_history(session_id)
    return jsonify({
        'history': [dict(row) for row in history],
        'success': True
    })

@app.route('/api/knowledge', methods=['GET'])
def get_knowledge():
    knowledge = hia.db.get_all_knowledge()
    return jsonify({
        'knowledge': [dict(row) for row in knowledge],
        'success': True
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    stats = hia.db.get_statistics()
    return jsonify({
        'statistics': stats,
        'success': True
    })

@app.route('/api/clear-memory', methods=['POST'])
def clear_memory():
    # د حافظې پاکولو لپاره (اختیاري)
    return jsonify({'message': 'Feature coming soon', 'success': True})

@app.route('/api/providers', methods=['GET'])
def get_providers():
    providers = [p.name for p in hia.providers]
    return jsonify({
        'providers': providers,
        'active': len(providers),
        'success': True
    })

# ============================================
# د اپلیکیشن چلول
# ============================================

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║      🤖 HIA AI Assistant v1.0        ║
    ║                                       ║
    ║  Server running on: http://localhost:5000
    ║                                       ║
    ╚═══════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)