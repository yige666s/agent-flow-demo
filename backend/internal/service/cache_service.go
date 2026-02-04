package service

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
)

type CacheService struct {
	client *redis.Client
	ttl    time.Duration
}

func NewCacheService(cfg interface{}) (*CacheService, error) {
	// TODO: Extract Redis config from cfg parameter
	client := redis.NewClient(&redis.Options{
		Addr:     "localhost:6379", // TODO: Use config
		Password: "",               // TODO: Use config
		DB:       0,                // TODO: Use config
	})

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &CacheService{
		client: client,
		ttl:    1 * time.Hour, // TODO: Make configurable
	}, nil
}

func (s *CacheService) GetRecommendation(ctx context.Context, query string) (interface{}, error) {
	key := s.generateKey(query)

	val, err := s.client.Get(ctx, key).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	var result interface{}
	if err := json.Unmarshal([]byte(val), &result); err != nil {
		return nil, err
	}

	return result, nil
}

func (s *CacheService) CacheRecommendation(ctx context.Context, query string, result interface{}) error {
	key := s.generateKey(query)

	data, err := json.Marshal(result)
	if err != nil {
		return err
	}

	return s.client.Set(ctx, key, data, s.ttl).Err()
}

func (s *CacheService) generateKey(query string) string {
	hash := md5.Sum([]byte(query))
	return fmt.Sprintf("recommend:%s", hex.EncodeToString(hash[:]))
}

func (s *CacheService) InvalidateCache(ctx context.Context, query string) error {
	key := s.generateKey(query)
	return s.client.Del(ctx, key).Err()
}

func (s *CacheService) Close() error {
	return s.client.Close()
}
