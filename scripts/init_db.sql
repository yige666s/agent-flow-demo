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
INSERT INTO templates (template_id, name, description, category, tags, style, color_scheme, use_case, status)
VALUES 
    ('tmpl_001', '简约商务海报', '适合产品发布会的简约风格海报模板', '海报', ARRAY['简约', '商务', '蓝色'], '简约', '蓝色主调', '产品发布', 'active'),
    ('tmpl_002', '科技感PPT模板', '现代科技风格的演示文稿模板', 'PPT', ARRAY['科技', '现代', '深色'], '科技', '深蓝黑', '产品展示', 'active'),
    ('tmpl_003', '温馨海报模板', '温暖色调的活动宣传海报', '海报', ARRAY['温馨', '活动', '暖色'], '温馨', '暖橙色', '活动宣传', 'active')
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
