"""
Comprehensive Logging System for Insurance Chatbot
Handles conversation logging, error tracking, and system monitoring
"""

import os
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from contextlib import contextmanager

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

@dataclass
class ChatLogEntry:
    """Structure for chat log entries"""
    timestamp: str
    conversation_id: str
    user_id: Optional[int]
    message_type: str  # user, assistant, system, error
    content: str
    metadata: Dict[str, Any]
    response_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    escalated: bool = False
    error_details: Optional[Dict[str, Any]] = None

@dataclass
class ErrorLogEntry:
    """Structure for error log entries"""
    timestamp: str
    conversation_id: str
    error_type: str
    error_message: str
    stack_trace: str
    context: Dict[str, Any]
    severity: str  # low, medium, high, critical
    resolved: bool = False
    resolution_notes: Optional[str] = None

class ChatLogger:
    """Comprehensive chat and error logging system"""
    
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        
    def setup_logging(self):
        """Configure Python logging"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(conversation_id)s] - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Chat logger
        self.chat_logger = logging.getLogger('chat')
        self.chat_logger.setLevel(logging.INFO)
        
        chat_handler = logging.FileHandler(LOGS_DIR / 'chat.log')
        chat_handler.setFormatter(detailed_formatter)
        self.chat_logger.addHandler(chat_handler)
        
        # Error logger
        self.error_logger = logging.getLogger('error')
        self.error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.FileHandler(LOGS_DIR / 'errors.log')
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
        
        # System logger
        self.system_logger = logging.getLogger('system')
        self.system_logger.setLevel(logging.INFO)
        
        system_handler = logging.FileHandler(LOGS_DIR / 'system.log')
        system_handler.setFormatter(simple_formatter)
        self.system_logger.addHandler(system_handler)
        
        # Console handler for development
        if os.getenv('FLASK_ENV') == 'development':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(simple_formatter)
            self.system_logger.addHandler(console_handler)
    
    def setup_database(self):
        """Setup SQLite database for structured logging"""
        self.db_path = LOGS_DIR / 'chat_logs.db'
        
        with self._get_db_connection() as conn:
            # Chat logs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    user_id INTEGER,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    response_time_ms REAL,
                    tokens_used INTEGER,
                    model_used TEXT,
                    escalated BOOLEAN DEFAULT FALSE,
                    error_details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Error logs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    context TEXT,
                    severity TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_conversation ON chat_logs(conversation_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_logs(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_error_conversation ON error_logs(conversation_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_error_severity ON error_logs(severity)')
    
    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_chat_message(self, 
                        conversation_id: str,
                        message_type: str,
                        content: str,
                        user_id: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None,
                        response_time_ms: Optional[float] = None,
                        tokens_used: Optional[int] = None,
                        model_used: Optional[str] = None,
                        escalated: bool = False):
        """Log a chat message"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_entry = ChatLogEntry(
            timestamp=timestamp,
            conversation_id=conversation_id,
            user_id=user_id,
            message_type=message_type,
            content=content[:1000] + "..." if len(content) > 1000 else content,  # Truncate long messages
            metadata=metadata or {},
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            model_used=model_used,
            escalated=escalated
        )
        
        # Log to file
        try:
            extra = {'conversation_id': conversation_id}
            self.chat_logger.info(
                f"{message_type.upper()} - {content[:100]}{'...' if len(content) > 100 else ''}", 
                extra=extra
            )
        except Exception:
            pass  # Don't let logging errors break the application
        
        # Log to database
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO chat_logs 
                    (timestamp, conversation_id, user_id, message_type, content, metadata, 
                     response_time_ms, tokens_used, model_used, escalated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry.timestamp,
                    log_entry.conversation_id,
                    log_entry.user_id,
                    log_entry.message_type,
                    log_entry.content,
                    json.dumps(log_entry.metadata),
                    log_entry.response_time_ms,
                    log_entry.tokens_used,
                    log_entry.model_used,
                    log_entry.escalated
                ))
        except Exception as e:
            print(f"Database logging failed: {e}")
        
        # Log to JSON file for easy parsing
        try:
            json_log_path = LOGS_DIR / f"chat_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(json_log_path, 'a') as f:
                f.write(json.dumps(asdict(log_entry)) + '\n')
        except Exception:
            pass
    
    def log_error(self,
                  conversation_id: str,
                  error: Exception,
                  context: Optional[Dict[str, Any]] = None,
                  severity: str = "medium"):
        """Log an error with full context"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        log_entry = ErrorLogEntry(
            timestamp=timestamp,
            conversation_id=conversation_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
            severity=severity
        )
        
        # Log to file
        try:
            extra = {'conversation_id': conversation_id}
            self.error_logger.error(
                f"{error_type}: {error_message}",
                extra=extra,
                exc_info=True
            )
        except Exception:
            pass
        
        # Log to database
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO error_logs 
                    (timestamp, conversation_id, error_type, error_message, stack_trace, context, severity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry.timestamp,
                    log_entry.conversation_id,
                    log_entry.error_type,
                    log_entry.error_message,
                    log_entry.stack_trace,
                    json.dumps(log_entry.context),
                    log_entry.severity
                ))
        except Exception:
            pass
        
        # Log critical errors to system log
        try:
            if severity == "critical":
                self.system_logger.critical(f"CRITICAL ERROR in {conversation_id}: {error_message}")
        except Exception:
            pass
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """Log system events"""
        try:
            self.system_logger.info(f"{event}: {json.dumps(details) if details else ''}")
        except Exception:
            pass
    
    def get_conversation_logs(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific conversation"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM chat_logs 
                    WHERE conversation_id = ? 
                    ORDER BY timestamp ASC
                ''', (conversation_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def get_error_logs(self, 
                       conversation_id: Optional[str] = None,
                       severity: Optional[str] = None,
                       resolved: Optional[bool] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get error logs with optional filtering"""
        
        try:
            query = "SELECT * FROM error_logs WHERE 1=1"
            params = []
            
            if conversation_id:
                query += " AND conversation_id = ?"
                params.append(conversation_id)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if resolved is not None:
                query += " AND resolved = ?"
                params.append(resolved)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with self._get_db_connection() as conn:
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def get_chat_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get chat statistics for the last N days"""
        try:
            with self._get_db_connection() as conn:
                # Total messages
                cursor = conn.execute('''
                    SELECT COUNT(*) as total_messages,
                           COUNT(DISTINCT conversation_id) as unique_conversations,
                           AVG(response_time_ms) as avg_response_time,
                           SUM(tokens_used) as total_tokens
                    FROM chat_logs 
                    WHERE timestamp >= datetime('now', '-{} days')
                '''.format(days))
                
                stats = dict(cursor.fetchone())
                
                # Messages by type
                cursor = conn.execute('''
                    SELECT message_type, COUNT(*) as count
                    FROM chat_logs 
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY message_type
                '''.format(days))
                
                stats['messages_by_type'] = {row['message_type']: row['count'] for row in cursor.fetchall()}
                
                # Escalations
                cursor = conn.execute('''
                    SELECT COUNT(*) as escalated_conversations
                    FROM chat_logs 
                    WHERE escalated = TRUE 
                    AND timestamp >= datetime('now', '-{} days')
                '''.format(days))
                
                stats['escalated_conversations'] = cursor.fetchone()['escalated_conversations']
                
                return stats
        except Exception:
            return {}
    
    def get_error_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get error statistics for the last N days"""
        try:
            with self._get_db_connection() as conn:
                # Total errors
                cursor = conn.execute('''
                    SELECT COUNT(*) as total_errors,
                           COUNT(DISTINCT conversation_id) as affected_conversations
                    FROM error_logs 
                    WHERE timestamp >= datetime('now', '-{} days')
                '''.format(days))
                
                stats = dict(cursor.fetchone())
                
                # Errors by severity
                cursor = conn.execute('''
                    SELECT severity, COUNT(*) as count
                    FROM error_logs 
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY severity
                '''.format(days))
                
                stats['errors_by_severity'] = {row['severity']: row['count'] for row in cursor.fetchall()}
                
                # Errors by type
                cursor = conn.execute('''
                    SELECT error_type, COUNT(*) as count
                    FROM error_logs 
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY error_type
                    ORDER BY count DESC
                    LIMIT 10
                '''.format(days))
                
                stats['top_error_types'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
        except Exception:
            return {}

    def resolve_error(self, error_id: int, resolution_notes: str):
        """Mark an error as resolved"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    UPDATE error_logs 
                    SET resolved = TRUE, resolution_notes = ?
                    WHERE id = ?
                ''', (resolution_notes, error_id))
        except Exception:
            pass

# Global logger instance
chat_logger = ChatLogger()

# Convenience functions
def log_chat(conversation_id: str, message_type: str, content: str, **kwargs):
    """Convenience function for logging chat messages"""
    chat_logger.log_chat_message(conversation_id, message_type, content, **kwargs)

def log_error(conversation_id: str, error: Exception, context: Dict[str, Any] = None, severity: str = "medium"):
    """Convenience function for logging errors"""
    chat_logger.log_error(conversation_id, error, context, severity)

def log_system(event: str, details: Dict[str, Any] = None):
    """Convenience function for logging system events"""
    chat_logger.log_system_event(event, details)