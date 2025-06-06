--
-- Adapted from https://github.com/DokiDoki1103/tikuAdapter under the MIT License.
--
-- Modifications made by niece

-- SET NAMES utf8mb4;
-- SET FOREIGN_KEY_CHECKS = 0;
--
-- ----------------------------
-- Table structure for tiku
-- ----------------------------
DROP TABLE IF EXISTS `tiku`;
CREATE TABLE tiku (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键
    question TEXT NOT NULL,               -- 问题原文（保留完整格式）
    question_text TEXT NOT NULL,          -- 清洗后的问题（仅汉字/数字/字母）
    question_hash TEXT NOT NULL,          -- 问题文本的哈希值
    type INTEGER NOT NULL ,               -- 题目类型
    options TEXT NOT NULL,                -- 选项（建议JSON格式存储）
    full_hash TEXT NOT NULL,              -- 完整题目哈希（问题+选项）
    source TEXT,                          -- 题目来源
    answer TEXT NOT NULL,                 -- 正确答案
    tags TEXT,                            -- 标签（逗号分隔或JSON）
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 新增：创建时间
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 新增：更新时间
);

-- 创建索引优化查询
CREATE INDEX idx_question_text ON tiku(question_text);  -- 模糊匹配索引
CREATE UNIQUE INDEX idx_full_hash ON tiku(full_hash);   -- 哈希唯一性索引