"""
数据库模型定义

使用SQLAlchemy ORM定义题库缓存的数据库结构。
主要包含三个核心表：
1. Question: 存储题目信息（使用归一化的题目内容和选项进行模糊匹配）
2. Answer: 存储各个provider的答案
3. QuestionProviderAnswer: 关联表，记录题目-provider-答案的关系

设计要点：
- 题目内容归一化：去除标点符号、空格，转小写，用于模糊匹配
- 选项归一化：排序后存储，避免选项顺序变化导致的不匹配
- 以provider为核心：每个provider的答案独立存储
- 支持批量查询：通过JOIN优化多provider查询性能
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Question(Base):
    """
    题目表

    存储题目的原始内容和归一化内容。
    归一化内容用于模糊匹配，解决标点符号、空格、大小写差异问题。
    """
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='题目ID')

    # 原始题目内容
    content = Column(Text, nullable=False, comment='题目原始内容')

    # 归一化后的题目内容（去除标点、空格、转小写）用于模糊匹配
    normalized_content = Column(Text, nullable=False, comment='归一化题目内容，用于模糊匹配')

    # 题目类型：0-单选，1-多选，2-填空，3-判断，4-问答
    type = Column(Integer, nullable=False, comment='题目类型：0-单选，1-多选，2-填空，3-判断，4-问答')

    # 选项（JSONB格式存储，可为null）
    options = Column(JSONB, nullable=True, comment='题目选项列表，JSONB格式')

    # 归一化后的选项（排序后的JSONB，用于匹配）
    normalized_options = Column(JSONB, nullable=True, comment='归一化选项列表（排序后），用于模糊匹配')

    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='最后更新时间')

    # 关联关系：一个题目可以有多个provider的答案
    provider_answers = relationship('QuestionProviderAnswer', back_populates='question', cascade='all, delete-orphan')

    # 索引：归一化内容 + 类型，用于快速查找相似题目
    # 注意：JSON字段使用GIN索引，需要PostgreSQL 9.4+
    __table_args__ = (
        Index('idx_normalized_content_type', 'normalized_content', 'type'),
        # JSON字段使用GIN索引（支持包含查询）
        Index('idx_normalized_options', 'normalized_options', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Question(id={self.id}, type={self.type}, content='{self.content[:50]}...')>"


class Answer(Base):
    """
    答案表

    存储各个provider返回的答案。
    同一个答案内容可能被多个题目-provider组合引用。
    """
    __tablename__ = 'answers'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='答案ID')

    # 答案类型（与题目类型对应）
    type = Column(Integer, nullable=False, comment='答案类型：0-单选，1-多选，2-填空，3-判断，4-问答')

    # 选择题答案（JSONB格式，如 ["A", "B"]）
    choice = Column(JSONB, nullable=True, comment='选择题答案，JSONB数组格式，如["A","B"]')

    # 判断题答案
    judgement = Column(Boolean, nullable=True, comment='判断题答案，True/False')

    # 填空题/问答题答案（JSONB格式，如 ["答案1", "答案2"]）
    text = Column(JSONB, nullable=True, comment='填空题/问答题答案，JSONB数组格式')

    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 关联关系：一个答案可以被多个题目-provider组合引用
    question_providers = relationship('QuestionProviderAnswer', back_populates='answer')

    # 索引：只在type字段上建索引，JSONB字段不建索引（通过关联表查询）
    __table_args__ = (
        Index('idx_answer_type', 'type'),
    )

    def __repr__(self):
        return f"<Answer(id={self.id}, type={self.type}, choice={self.choice}, judgement={self.judgement})>"


class QuestionProviderAnswer(Base):
    """
    题目-Provider-答案关联表

    记录某个题目在某个provider下的答案。
    这是核心关联表，支持：
    1. 查询某个题目在特定provider下的缓存答案
    2. 批量查询某个题目在多个provider下的答案
    3. 更新某个题目在特定provider下的答案
    """
    __tablename__ = 'question_provider_answers'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='关联ID')

    # 题目ID（外键）
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, comment='题目ID')

    # Provider名称（如 "Like知识库"、"万能题库"）
    provider_name = Column(String(100), nullable=False, comment='Provider名称')

    # 答案ID（外键）
    answer_id = Column(Integer, ForeignKey('answers.id', ondelete='CASCADE'), nullable=False, comment='答案ID')

    # Provider配置的哈希值（用于区分同一provider不同配置的缓存）
    # 例如：Like知识库使用不同的model参数可能返回不同答案
    config_hash = Column(String(64), nullable=True, comment='Provider配置的哈希值，用于区分不同配置')

    # 答案置信度/优先级（可选，用于后续优化答案聚合）
    confidence = Column(Integer, default=100, comment='答案置信度，0-100，默认100')

    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='最后更新时间')

    # 关联关系
    question = relationship('Question', back_populates='provider_answers')
    answer = relationship('Answer', back_populates='question_providers')

    # 索引：核心查询索引
    __table_args__ = (
        # 联合唯一索引：同一题目+provider+配置只能有一个答案
        Index('idx_unique_question_provider', 'question_id', 'provider_name', 'config_hash', unique=True),
        # 查询索引：根据题目ID批量查询多个provider
        Index('idx_question_providers', 'question_id', 'provider_name'),
        # 查询索引：根据provider查询所有缓存
        Index('idx_provider_name', 'provider_name'),
    )

    def __repr__(self):
        return f"<QuestionProviderAnswer(question_id={self.question_id}, provider={self.provider_name}, answer_id={self.answer_id})>"