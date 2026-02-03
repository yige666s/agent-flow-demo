package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Config 全局配置
type Config struct {
	Server  ServerConfig  `yaml:"server"`
	Agent   AgentConfig   `yaml:"agent"`
	Worker  WorkerConfig  `yaml:"worker"`
	Storage StorageConfig `yaml:"storage"`
	Logging LoggingConfig `yaml:"logging"`
}

// ServerConfig 服务器配置
type ServerConfig struct {
	Host    string `yaml:"host"`
	Port    int    `yaml:"port"`
	Timeout int    `yaml:"timeout"` // 秒
}

// AgentConfig Agent 配置
type AgentConfig struct {
	PythonServiceURL string `yaml:"python_service_url"`
	RequestTimeout   int    `yaml:"request_timeout"` // 秒
	MaxRetries       int    `yaml:"max_retries"`
}

// WorkerConfig Worker 配置
type WorkerConfig struct {
	PoolSize  int `yaml:"pool_size"`
	QueueSize int `yaml:"queue_size"`
}

// StorageConfig 存储配置
type StorageConfig struct {
	Type  string      `yaml:"type"` // redis / json
	Redis RedisConfig `yaml:"redis"`
	JSON  JSONConfig  `yaml:"json"`
}

// RedisConfig Redis 配置
type RedisConfig struct {
	Host     string `yaml:"host"`
	Port     int    `yaml:"port"`
	DB       int    `yaml:"db"`
	Password string `yaml:"password"`
}

// JSONConfig JSON 文件存储配置
type JSONConfig struct {
	DataDir string `yaml:"data_dir"`
}

// LoggingConfig 日志配置
type LoggingConfig struct {
	Level  string `yaml:"level"`  // debug / info / warn / error
	Format string `yaml:"format"` // json / text
	Output string `yaml:"output"` // stdout / file
}

// LoadConfig 加载配置文件
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	return &cfg, nil
}

// GetAddress 获取服务器地址
func (s *ServerConfig) GetAddress() string {
	return fmt.Sprintf("%s:%d", s.Host, s.Port)
}
