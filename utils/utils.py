
from typing import Dict, List
import json
from datetime import datetime, timedelta


class TokenOptimizer:
   
    
    @staticmethod
    def compress_history(messages: List[Dict]) -> List[Dict]:
        
        if len(messages) <= 5:
            return messages
        
        
        return [messages[0]] + messages[-5:]
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        
        words = len(text.split())
        chars = len(text)
        return max(words, chars // 4)
    
    @staticmethod
    def truncate_text(text: str, max_tokens: int = 100) -> str:
        
        estimated = TokenOptimizer.estimate_tokens(text)
        
        if estimated <= max_tokens:
            return text
        
     
        ratio = max_tokens / estimated
        target_length = int(len(text) * ratio)
        
        return text[:target_length] + "..."


class AnalyticsManager:
    
    def __init__(self, db):
        self.db = db
    
    def get_usage_stats(self, trader_id: str = None, days: int = 30) -> Dict:
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        date_filter = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        if trader_id:
           
            cursor.execute("""
                SELECT 
                    COUNT(*) as message_count,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message
                FROM chat_history
                WHERE trader_id = ? AND created_at >= ?
            """, (trader_id, date_filter))
        else:
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as message_count,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens,
                    MIN(created_at) as first_message,
                    MAX(created_at) as last_message
                FROM chat_history
                WHERE created_at >= ?
            """, (date_filter,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:
            return {
                "message_count": row[0],
                "total_tokens": row[1] or 0,
                "avg_tokens_per_message": round(row[2] or 0, 2),
                "first_message": row[3],
                "last_message": row[4],
                "estimated_cost_usd": round((row[1] or 0) / 1_000_000 * 0.30, 4),
                "period_days": days
            }
        
        return {"message_count": 0, "total_tokens": 0}
    
    def get_top_traders(self, limit: int = 10) -> List[Dict]:
       
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.trader_id,
                t.name,
                COUNT(c.id) as message_count,
                SUM(c.tokens_used) as total_tokens
            FROM traders t
            LEFT JOIN chat_history c ON t.trader_id = c.trader_id
            GROUP BY t.trader_id
            ORDER BY message_count DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "trader_id": row[0],
                "name": row[1],
                "message_count": row[2],
                "total_tokens": row[3] or 0
            }
            for row in rows
        ]
    
    def get_hourly_distribution(self, trader_id: str = None) -> Dict:
       
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if trader_id:
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', created_at) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM chat_history
                WHERE trader_id = ?
                GROUP BY hour
                ORDER BY hour
            """, (trader_id,))
        else:
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', created_at) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM chat_history
                GROUP BY hour
                ORDER BY hour
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        
        distribution = {hour: 0 for hour in range(24)}
        for hour, count in rows:
            distribution[hour] = count
        
        return distribution


class CacheManager:
    
    
    def __init__(self, cache_file: str = "response_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
       
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_cache(self):
       
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f" فشل حفظ الـ cache: {e}")
    
    def get(self, query: str) -> str:
        
        query_normalized = query.strip().lower()
        return self.cache.get(query_normalized)
    
    def set(self, query: str, response: str):
        
        query_normalized = query.strip().lower()
        self.cache[query_normalized] = {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "hit_count": self.cache.get(query_normalized, {}).get("hit_count", 0) + 1
        }
        self._save_cache()
    
    def clear(self):
        """مسح الـ cache"""
        self.cache = {}
        self._save_cache()
    
    def get_stats(self) -> Dict:
        """إحصائيات الـ cache"""
        return {
            "total_entries": len(self.cache),
            "total_hits": sum(entry.get("hit_count", 0) for entry in self.cache.values())
        }


class ExportManager:
    """تصدير البيانات لصيغ مختلفة"""
    
    @staticmethod
    def export_history_to_txt(history: List[tuple], output_file: str):
        """تصدير السجل إلى ملف نصي"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("سجل المحادثات\n")
                f.write("=" * 60 + "\n\n")
                
                for msg_type, content, timestamp in history:
                    if msg_type == "user":
                        f.write(f" [{timestamp}]\n")
                        f.write(f"{content}\n\n")
                    else:
                        f.write(f" [{timestamp}]\n")
                        f.write(f"{content}\n\n")
                    f.write("-" * 60 + "\n\n")
            
            print(f" تم التصدير إلى: {output_file}")
            return True
        except Exception as e:
            print(f" فشل التصدير: {e}")
            return False
    
    @staticmethod
    def export_history_to_json(history: List[tuple], output_file: str):
        """تصدير السجل إلى JSON"""
        try:
            data = []
            for msg_type, content, timestamp in history:
                data.append({
                    "type": msg_type,
                    "content": content,
                    "timestamp": timestamp
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f" تم التصدير إلى: {output_file}")
            return True
        except Exception as e:
            print(f" فشل التصدير: {e}")
            return False


class QueryAnalyzer:
    """تحليل نوع الاستفسار"""
    
    # كلمات مفتاحية لتصنيف الاستفسارات
    CATEGORIES = {
        "ضرائب": ["ضريبة", "زكاة", "القيمة المضافة", "الدخل", "ضريبي"],
        "تراخيص": ["ترخيص", "سجل تجاري", "رخصة", "تصريح"],
        "عمالة": ["عامل", "موظف", "كفيل", "عمالة", "استقدام", "قوى"],
        "جمارك": ["جمارك", "استيراد", "تصدير", "شحن"],
        "منصات": ["مراس", "بلدي", "قوى", "أبشر", "منصة"],
        "قانوني": ["نظام", "قانون", "لائحة", "مخالفة", "عقوبة"],
        "عام": []
    }
    
    @staticmethod
    def categorize_query(query: str) -> str:
        """تصنيف الاستفسار"""
        query_lower = query.lower()
        
        for category, keywords in QueryAnalyzer.CATEGORIES.items():
            if category == "عام":
                continue
            
            for keyword in keywords:
                if keyword in query_lower:
                    return category
        
        return "عام"
    
    @staticmethod
    def is_greeting(query: str) -> bool:
        """التحقق إذا كان الاستفسار تحية"""
        greetings = ["السلام", "مرحبا", "أهلا", "صباح", "مساء", "كيف حالك"]
        query_lower = query.lower()
        return any(greeting in query_lower for greeting in greetings)
    
    @staticmethod
    def extract_keywords(query: str) -> List[str]:
        """استخراج الكلمات المفتاحية"""
        # كلمات توقف عربية
        stop_words = {
            "في", "من", "إلى", "على", "عن", "ما", "هو", "هي", "أنا",
            "أنت", "هل", "كيف", "ماذا", "متى", "أين", "لماذا", "و", "أو"
        }
        
        words = query.split()
        keywords = [
            word.strip("؟.,!") 
            for word in words 
            if len(word) > 2 and word not in stop_words
        ]
        
        return keywords[:5]  # أول 5 كلمات مفتاحية


class ResponseEnhancer:
    """تحسين الاستجابات"""
    
    @staticmethod
    def add_related_links(response: str, category: str) -> str:
        """إضافة روابط ذات صلة"""
        links = {
            "ضرائب": "\n\n روابط مفيدة:\n• الهيئة العامة للزكاة والدخل: zatca.gov.sa",
            "تراخيص": "\n\n روابط مفيدة:\n• وزارة التجارة: mc.gov.sa\n• السجل التجاري: cr.mc.gov.sa",
            "عمالة": "\n\n روابط مفيدة:\n• منصة قوى: qiwa.sa\n• وزارة الموارد البشرية: hrsd.gov.sa",
            "منصات": "\n\n روابط مفيدة:\n• منصة مراس: marasi.sa\n• بوابة الخدمات: my.gov.sa"
        }
        
        return response + links.get(category, "")
    
    @staticmethod
    def format_response(response: str) -> str:
        """تنسيق الاستجابة"""
        # إضافة رموز تعبيرية للنقاط
        response = response.replace("- ", "• ")
        
        # تحسين المسافات
        response = response.replace("\n\n\n", "\n\n")
        
        return response.strip()


class BackupManager:
    """إدارة النسخ الاحتياطي"""
    
    @staticmethod
    def backup_database(db_path: str, backup_folder: str = "backups"):
        """نسخ احتياطي لقاعدة البيانات"""
        import shutil
        import os
        
        try:
            os.makedirs(backup_folder, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                backup_folder, 
                f"backup_{timestamp}.db"
            )
            
            shutil.copy2(db_path, backup_file)
            print(f" تم إنشاء نسخة احتياطية: {backup_file}")
            return backup_file
        
        except Exception as e:
            print(f" فشل النسخ الاحتياطي: {e}")
            return None
    
    @staticmethod
    def restore_database(backup_file: str, db_path: str):
        """استعادة قاعدة البيانات"""
        import shutil
        
        try:
            # نسخ احتياطي للملف الحالي أولاً
            current_backup = f"{db_path}.before_restore"
            shutil.copy2(db_path, current_backup)
            
            # استعادة النسخة
            shutil.copy2(backup_file, db_path)
            print(f" تم استعادة قاعدة البيانات من: {backup_file}")
            return True
        
        except Exception as e:
            print(f" فشل الاستعادة: {e}")
            return False


# دوال مساعدة سريعة
def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}"


def calculate_cost(tokens: int, model: str = "gpt-4o-mini") -> Dict:
    """حساب التكلفة بناءً على النموذج"""
    costs = {
        "gpt-4o-mini": 0.30 / 1_000_000,  # متوسط
        "gpt-4o": 5.00 / 1_000_000,
        "gpt-3.5-turbo": 1.50 / 1_000_000
    }
    
    cost_per_token = costs.get(model, costs["gpt-4o-mini"])
    cost_usd = tokens * cost_per_token
    cost_sar = cost_usd * 3.75
    
    return {
        "tokens": tokens,
        "cost_usd": round(cost_usd, 6),
        "cost_sar": round(cost_sar, 4)
    }


def get_time_greeting() -> str:
    """تحية حسب الوقت"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "صباح الخير"
    elif 12 <= hour < 17:
        return "مساء الخير"
    elif 17 <= hour < 21:
        return "مساء الخير"
    else:
        return "مساء الخير"


def validate_trader_id(trader_id: str) -> bool:
    """التحقق من صحة معرف التاجر"""
    # يجب أن يكون بين 3-20 حرف وأرقام فقط
    if not trader_id:
        return False
    
    if len(trader_id) < 3 or len(trader_id) > 20:
        return False
    
    # يمكن أن يحتوي على حروف وأرقام و-_
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return all(c in allowed for c in trader_id)