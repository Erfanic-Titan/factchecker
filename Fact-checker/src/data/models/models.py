"""
مدل‌های پایگاه داده برای ذخیره اطلاعات مربوط به راستی‌آزمایی.
این ماژول شامل تعاریف تمام جداول و روابط بین آنهاست.
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, 
    Integer, JSON, String, Table, Text
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.schema import Index

Base = declarative_base()

class User(Base):
    """مدل کاربران سیستم."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default='fa')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    
    # تنظیمات کاربر
    settings = Column(JSON, default={})
    
    # روابط
    claims = relationship('Claim', back_populates='user')
    feedback = relationship('Feedback', back_populates='user')
    comments = relationship('Comment', back_populates='user')
    reports = relationship('Report', back_populates='user')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_telegram_id', 'telegram_id'),
    )

class Claim(Base):
    """مدل ادعاهای ارسالی برای راستی‌آزمایی."""
    
    __tablename__ = 'claims'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(
        Enum('TEXT', 'IMAGE', 'VIDEO', 'VOICE', 'DOCUMENT', 'LINK', name='claim_types'),
        nullable=False
    )
    language = Column(String(10), default='fa')
    metadata = Column(JSON)  # برای ذخیره اطلاعات اضافی مثل فایل‌ها
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(
        Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='claim_statuses'),
        default='PENDING'
    )
    
    # روابط
    user = relationship('User', back_populates='claims')
    fact_checks = relationship('FactCheck', back_populates='claim')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_claim_status', 'status'),
        Index('idx_claim_created', 'created_at'),
    )

class FactCheck(Base):
    """مدل نتایج راستی‌آزمایی."""
    
    __tablename__ = 'fact_checks'
    
    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey('claims.id'), nullable=False)
    verification_status = Column(
        Enum(
            'VERIFIED', 'FALSE', 'PARTIALLY_TRUE', 
            'UNVERIFIED', 'MISLEADING',
            name='verification_statuses'
        ),
        nullable=False
    )
    credibility_score = Column(Float, nullable=False)
    analysis_result = Column(JSON)  # نتایج تحلیل
    evidence = Column(JSON)  # شواهد و مستندات
    sources = Column(JSON)  # منابع مورد استفاده
    metadata = Column(JSON)  # اطلاعات اضافی
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # روابط
    claim = relationship('Claim', back_populates='fact_checks')
    feedback = relationship('Feedback', back_populates='fact_check')
    comments = relationship('Comment', back_populates='fact_check')
    reports = relationship('Report', back_populates='fact_check')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_verification_status', 'verification_status'),
        Index('idx_credibility_score', 'credibility_score'),
    )

class Source(Base):
    """مدل منابع معتبر."""
    
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    source_type = Column(
        Enum(
            'NEWS', 'ACADEMIC', 'GOVERNMENT', 'FACT_CHECK',
            name='source_types'
        ),
        nullable=False
    )
    base_credibility = Column(Float, default=0.5)  # امتیاز اعتبار پایه
    api_config = Column(JSON)  # تنظیمات API
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_source_type', 'source_type'),
        Index('idx_source_domain', 'domain'),
    )

class Feedback(Base):
    """مدل بازخوردهای کاربران."""
    
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    fact_check_id = Column(Integer, ForeignKey('fact_checks.id'), nullable=False)
    feedback_type = Column(
        Enum('AGREE', 'DISAGREE', name='feedback_types'),
        nullable=False
    )
    created_at = Column(DateTime, default=func.now())
    
    # روابط
    user = relationship('User', back_populates='feedback')
    fact_check = relationship('FactCheck', back_populates='feedback')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_feedback_type', 'feedback_type'),
    )

class Comment(Base):
    """مدل نظرات کاربران."""
    
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    fact_check_id = Column(Integer, ForeignKey('fact_checks.id'), nullable=False)
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # روابط
    user = relationship('User', back_populates='comments')
    fact_check = relationship('FactCheck', back_populates='comments')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_comment_approved', 'is_approved'),
    )

class Report(Base):
    """مدل گزارش‌های مشکل."""
    
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    fact_check_id = Column(Integer, ForeignKey('fact_checks.id'), nullable=False)
    report_type = Column(
        Enum(
            'INCORRECT', 'INAPPROPRIATE', 'MISLEADING',
            'SPAM', 'OTHER',
            name='report_types'
        ),
        nullable=False
    )
    description = Column(Text)
    status = Column(
        Enum('PENDING', 'REVIEWING', 'RESOLVED', 'REJECTED', name='report_statuses'),
        default='PENDING'
    )
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # روابط
    user = relationship('User', back_populates='reports')
    fact_check = relationship('FactCheck', back_populates='reports')
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_report_status', 'status'),
        Index('idx_report_type', 'report_type'),
    )

# Association Tables برای روابط چند به چند

fact_check_sources = Table(
    'fact_check_sources',
    Base.metadata,
    Column('fact_check_id', Integer, ForeignKey('fact_checks.id'), primary_key=True),
    Column('source_id', Integer, ForeignKey('sources.id'), primary_key=True),
    Column('relevance_score', Float),  # امتیاز ارتباط منبع با ادعا
    Column('created_at', DateTime, default=func.now())
)

similar_claims = Table(
    'similar_claims',
    Base.metadata,
    Column('claim_id', Integer, ForeignKey('claims.id'), primary_key=True),
    Column('similar_claim_id', Integer, ForeignKey('claims.id'), primary_key=True),
    Column('similarity_score', Float),  # امتیاز شباهت
    Column('created_at', DateTime, default=func.now())
)