package config

import (
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	Milvus   MilvusConfig
	Agent    AIServiceConfig `mapstructure:"agent"`
	RabbitMQ RabbitMQConfig
	MinIO    MinIOConfig
}

type ServerConfig struct {
	Host         string
	Port         int
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

type DatabaseConfig struct {
	Host     string
	Port     int
	User     string
	Password string
	DBName   string
	SSLMode  string
}

type RedisConfig struct {
	Host     string
	Port     int
	Password string
	DB       int
}

type MilvusConfig struct {
	Host string
	Port int
}

type AIServiceConfig struct {
	Host         string
	Port         int
	EmbeddingDim int `mapstructure:"embedding_dim"`
}

type RabbitMQConfig struct {
	Host     string
	Port     int
	User     string
	Password string
}

type MinIOConfig struct {
	Endpoint  string
	AccessKey string
	SecretKey string
	UseSSL    bool
	Bucket    string
}

func Load() (*Config, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	viper.AddConfigPath("./backend")

	// TODO: Set default configuration values
	setDefaults()

	if err := viper.ReadInConfig(); err != nil {
		return nil, err
	}

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func setDefaults() {
	// Server defaults
	viper.SetDefault("server.host", "0.0.0.0")
	viper.SetDefault("server.port", 8080)
	viper.SetDefault("server.readTimeout", "10s")
	viper.SetDefault("server.writeTimeout", "10s")

	// TODO: Database defaults - configure based on your environment
	viper.SetDefault("database.host", "localhost")
	viper.SetDefault("database.port", 5432)
	viper.SetDefault("database.user", "postgres")
	viper.SetDefault("database.password", "postgres")
	viper.SetDefault("database.dbname", "templates")
	viper.SetDefault("database.sslmode", "disable")

	// TODO: Redis defaults - configure based on your environment
	viper.SetDefault("redis.host", "localhost")
	viper.SetDefault("redis.port", 6379)
	viper.SetDefault("redis.password", "")
	viper.SetDefault("redis.db", 0)

	// TODO: Milvus defaults - configure based on your environment
	viper.SetDefault("milvus.host", "localhost")
	viper.SetDefault("milvus.port", 19530)

	// AI Service (Agent) defaults
	viper.SetDefault("agent.host", "localhost")
	viper.SetDefault("agent.port", 50051)
	viper.SetDefault("agent.embedding_dim", 1536)

	// TODO: RabbitMQ defaults - configure based on your environment
	viper.SetDefault("rabbitmq.host", "localhost")
	viper.SetDefault("rabbitmq.port", 5672)
	viper.SetDefault("rabbitmq.user", "guest")
	viper.SetDefault("rabbitmq.password", "guest")

	// TODO: MinIO defaults - configure based on your environment
	viper.SetDefault("minio.endpoint", "localhost:9000")
	viper.SetDefault("minio.accessKey", "minioadmin")
	viper.SetDefault("minio.secretKey", "minioadmin")
	viper.SetDefault("minio.useSSL", false)
	viper.SetDefault("minio.bucket", "templates")
}
