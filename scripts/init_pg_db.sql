-- Database initialization script for template recommendation system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable array functions
CREATE EXTENSION IF NOT EXISTS "intarray";

-- Templates table
CREATE TABLE IF NOT EXISTS templates (
    id BIGSERIAL PRIMARY KEY,
    template_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    tags TEXT[],
    style VARCHAR(50),
    color_scheme VARCHAR(50),
    use_case VARCHAR(100),
    thumbnail_url VARCHAR(512),
    preview_url VARCHAR(512),
    file_url VARCHAR(512),
    vector_id VARCHAR(64),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    
    -- Statistics
    view_count INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_template_id ON templates(template_id);
CREATE INDEX IF NOT EXISTS idx_category ON templates(category);
CREATE INDEX IF NOT EXISTS idx_tags ON templates USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_style ON templates(style);
CREATE INDEX IF NOT EXISTS idx_status ON templates(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON templates(created_at);

-- User interactions table
CREATE TABLE IF NOT EXISTS user_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64),
    query TEXT NOT NULL,
    intent JSONB,
    recommended_templates JSONB,
    selected_template_id VARCHAR(64),
    feedback VARCHAR(20),
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for user_interactions
CREATE INDEX IF NOT EXISTS idx_user_interactions_user_id ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_session_id ON user_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_created_at ON user_interactions(created_at);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(100),
    email VARCHAR(255),
    preferences JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for users
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);

-- Insert sample data (TODO: Replace with actual template data)
INSERT INTO templates (
    template_id, name, description, category, tags,
    style, color_scheme, use_case,
    thumbnail_url, preview_url, file_url,
    vector_id, status
) VALUES
-- 1
('tmpl_002', '科技发布会主视觉', '科技感强烈的新品发布会主视觉模板', '海报',
 ARRAY['科技', '发布会', '深色'], '科技风', '深蓝+霓虹', '新品发布',
 NULL, NULL, NULL, NULL, 'active'),

-- 2 (skipped for brevity in planning, but included in actual replacement)
-- ... [I will include all items in the actual replacement call] ...
('tmpl_003', '电商促销主图', '适用于电商平台大促活动的商品主图模板', '电商',
 ARRAY['电商', '促销', '高转化'], '促销风', '红色+黄色', '电商大促',
 NULL, NULL, NULL, NULL, 'active'),

-- 3
('tmpl_004', '极简产品介绍页', '突出产品卖点的极简风格介绍页', '网页',
 ARRAY['极简', '产品', '展示'], '极简', '黑白灰', '产品介绍',
 NULL, NULL, NULL, NULL, 'active'),

-- 4
('tmpl_005', '社交媒体宣传海报', '适合微博、Twitter、Instagram 使用的宣传海报', '海报',
 ARRAY['社交媒体', '宣传', '品牌'], '现代', '高饱和度', '品牌推广',
 NULL, NULL, NULL, NULL, 'active'),

-- 5
('tmpl_006', '企业官网首页', '企业官网首页视觉模板，稳重专业', '网页',
 ARRAY['企业官网', '正式', '专业'], '商务风', '蓝灰色', '企业官网',
 NULL, NULL, NULL, NULL, 'active'),

-- 6
('tmpl_007', '课程封面模板', '在线课程、训练营通用封面设计', '教育',
 ARRAY['课程', '教育', '知识付费'], '扁平化', '绿色主调', '课程推广',
 NULL, NULL, NULL, NULL, 'active'),

-- 7
('tmpl_008', 'APP 启动页', '移动应用启动页设计模板', '移动端',
 ARRAY['APP', '启动页', 'UI'], '现代UI', '渐变色', 'APP 启动',
 NULL, NULL, NULL, NULL, 'active'),

-- 8
('tmpl_009', 'SaaS 产品介绍页', 'SaaS 官网产品功能介绍模板', '网页',
 ARRAY['SaaS', '产品介绍', 'B端'], '科技风', '蓝紫渐变', 'SaaS 官网',
 NULL, NULL, NULL, NULL, 'active'),

-- 9
('tmpl_010', '招聘宣传海报', '企业招聘用宣传海报模板', '海报',
 ARRAY['招聘', '企业文化', 'HR'], '商务风', '蓝橙配色', '招聘宣传',
 NULL, NULL, NULL, NULL, 'active'),

-- 10
('tmpl_011', '品牌故事长图', '讲述品牌故事的长图模板', '长图',
 ARRAY['品牌故事', '情感', '营销'], '叙事风', '暖色调', '品牌传播',
 NULL, NULL, NULL, NULL, 'active'),

-- 11
('tmpl_012', '活动邀请函', '线上线下活动通用邀请函模板', '物料',
 ARRAY['活动', '邀请函', '正式'], '简约', '白金色', '活动邀请',
 NULL, NULL, NULL, NULL, 'active'),

-- 12
('tmpl_013', '数据分析报告封面', '数据分析与年度报告封面设计', '报告',
 ARRAY['数据', '分析', '报告'], '专业风', '深蓝色', '数据汇报',
 NULL, NULL, NULL, NULL, 'active'),

-- 13
('tmpl_014', '短视频封面', '抖音 / YouTube Shorts 视频封面模板', '视频',
 ARRAY['短视频', '封面', '自媒体'], '高对比', '亮色系', '视频封面',
 NULL, NULL, NULL, NULL, 'active'),

-- 14
('tmpl_015', '产品功能对比图', '突出产品差异化的对比图模板', '图表',
 ARRAY['对比', '功能', '产品'], '信息图', '蓝绿配色', '产品对比',
 NULL, NULL, NULL, NULL, 'active'),

-- 15
('tmpl_016', '新用户引导页', '新用户 onboarding 引导页面', '移动端',
 ARRAY['引导页', '新手', '体验'], '现代UI', '柔和渐变', '用户引导',
 NULL, NULL, NULL, NULL, 'active'),

-- 16
('tmpl_017', '节日促销海报', '双十一、黑五等节日促销海报', '海报',
 ARRAY['节日', '促销', '转化'], '促销风', '红黑配色', '节日营销',
 NULL, NULL, NULL, NULL, 'active'),

-- 17
('tmpl_018', '品牌VI展示页', '品牌视觉规范展示模板', '品牌',
 ARRAY['VI', '品牌规范', '设计'], '规范化', '品牌主色', '品牌VI',
 NULL, NULL, NULL, NULL, 'active'),

-- 18
('tmpl_019', '营销落地页', '高转化营销 Landing Page 模板', '网页',
 ARRAY['落地页', '营销', '转化'], '营销风', '橙色主调', '广告投放',
 NULL, NULL, NULL, NULL, 'active'),

-- 19
('tmpl_020', '用户评价展示页', '客户评价、案例展示模板', '网页',
 ARRAY['评价', '口碑', '信任'], '简约', '浅色系', '用户背书',
 NULL, NULL, NULL, NULL, 'active'),

-- 20
('tmpl_021', 'APP 功能介绍长图', '移动应用功能介绍长图', '长图',
 ARRAY['APP', '功能介绍', '说明'], '信息图', '蓝白配色', '功能说明',
 NULL, NULL, NULL, NULL, 'active'),

-- 21
('tmpl_022', '新品预告海报', '新品上线前预热海报模板', '海报',
 ARRAY['新品', '预热', '悬念'], '潮流', '暗色调', '新品预告',
 NULL, NULL, NULL, NULL, 'active'),

-- 22
('tmpl_023', '博客封面图', '技术 / 内容博客通用封面模板', '内容',
 ARRAY['博客', '内容创作', '技术'], '极简', '灰蓝色', '内容创作',
 NULL, NULL, NULL, NULL, 'active'),

-- 23
('tmpl_024', '演示文稿封面', 'PPT / Keynote 演示封面设计', '演示',
 ARRAY['PPT', '演示', '汇报'], '商务风', '深蓝渐变', '演示汇报',
 NULL, NULL, NULL, NULL, 'active'),

-- 24
('tmpl_025', '产品定价页', 'SaaS 产品定价页面模板', '网页',
 ARRAY['定价', 'SaaS', '转化'], '简洁', '蓝白配色', '产品定价',
 NULL, NULL, NULL, NULL, 'active'),

-- 25
('tmpl_026', '品牌社群宣传图', '社群拉新与运营宣传模板', '社群',
 ARRAY['社群', '增长', '运营'], '活泼', '亮色系', '社群推广',
 NULL, NULL, NULL, NULL, 'active'),

-- 26
('tmpl_027', '电商详情页头图', '商品详情页顶部视觉模板', '电商',
 ARRAY['电商', '详情页', '商品'], '写实', '中性色', '商品展示',
 NULL, NULL, NULL, NULL, 'active'),

-- 27
('tmpl_028', '品牌周年庆海报', '企业周年庆典宣传模板', '海报',
 ARRAY['周年庆', '品牌', '庆典'], '庆典风', '金色红色', '品牌活动',
 NULL, NULL, NULL, NULL, 'active'),

-- 28
('tmpl_029', '技术架构示意图', '技术架构与系统流程展示模板', '技术',
 ARRAY['架构图', '系统设计', '技术'], '技术风', '蓝灰色', '技术说明',
 NULL, NULL, NULL, NULL, 'active'),

-- 29
('tmpl_030', '用户增长分析图', '用户增长与漏斗分析模板', '数据',
 ARRAY['增长', '分析', '数据'], '数据可视化', '蓝绿色', '数据分析',
 NULL, NULL, NULL, NULL, 'active'),

-- 30
('tmpl_031', '国际化官网首页', '面向海外用户的国际化官网首页模板', '网页',
 ARRAY['国际化', '海外', '官网'], '现代', '浅色国际风', '海外官网',
 NULL, NULL, NULL, NULL, 'active')
ON CONFLICT (template_id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (TODO: Configure for production)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
