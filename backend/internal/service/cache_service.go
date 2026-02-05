package service

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/milvus-io/milvus-sdk-go/v2/client"
	"github.com/milvus-io/milvus-sdk-go/v2/entity"

	ailient "template-recommend/internal/client"
	"template-recommend/internal/config"
)

type CacheService struct {
	redisClient    *redis.Client
	milvusClient   client.Client
	aiClient       *ailient.AIServiceClient
	collectionName string
	dimension      int
	threshold      float32 // L2 距离阈值，越小越相似。建议：0.1~0.2
	ttl            time.Duration
}

func NewCacheService(cfg *config.Config, aiClient *ailient.AIServiceClient) (*CacheService, error) {
	// 1. Connect Redis
	redisClient := redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", cfg.Redis.Host, cfg.Redis.Port),
		Password: cfg.Redis.Password,
		DB:       cfg.Redis.DB,
	})

	// 2. Connect Milvus
	milvusClient, err := client.NewGrpcClient(
		context.Background(),
		fmt.Sprintf("%s:%d", cfg.Milvus.Host, cfg.Milvus.Port),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Milvus: %w", err)
	}

	svc := &CacheService{
		redisClient:    redisClient,
		milvusClient:   milvusClient,
		aiClient:       aiClient,
		collectionName: "query_cache",
		dimension:      cfg.Agent.EmbeddingDim,
		threshold:      0.15, // L2 距离。如果你用 IP (内积)，则越接近 1 越好
		ttl:            24 * time.Hour,
	}

	// 3. Initialize Milvus collection for query cache
	if err := svc.initCollection(context.Background()); err != nil {
		return nil, fmt.Errorf("failed to init query cache collection: %w", err)
	}

	return svc, nil
}

func (s *CacheService) initCollection(ctx context.Context) error {
	has, err := s.milvusClient.HasCollection(ctx, s.collectionName)
	if err != nil {
		return err
	}
	if has {
		_ = s.milvusClient.LoadCollection(ctx, s.collectionName, false)
		return nil
	}

	schema := &entity.Schema{
		CollectionName: s.collectionName,
		Description:    "Semantic query cache collection",
		Fields: []*entity.Field{
			{Name: "id", DataType: entity.FieldTypeInt64, PrimaryKey: true, AutoID: true},
			{Name: "query_hash", DataType: entity.FieldTypeVarChar, TypeParams: map[string]string{"max_length": "64"}},
			{Name: "query_text", DataType: entity.FieldTypeVarChar, TypeParams: map[string]string{"max_length": "500"}},
			{Name: "embedding", DataType: entity.FieldTypeFloatVector, TypeParams: map[string]string{"dim": fmt.Sprintf("%d", s.dimension)}},
		},
	}

	if err := s.milvusClient.CreateCollection(ctx, schema, entity.DefaultShardNumber); err != nil {
		return err
	}

	idx, _ := entity.NewIndexHNSW(entity.L2, 8, 200)
	_ = s.milvusClient.CreateIndex(ctx, s.collectionName, "embedding", idx, false)
	_ = s.milvusClient.LoadCollection(ctx, s.collectionName, false)
	return nil
}

func (s *CacheService) GetRecommendation(ctx context.Context, query string) (interface{}, error) {
	// 先尝试精确匹配 (Fast path)
	hashKey := s.generateKey(query)
	val, err := s.redisClient.Get(ctx, hashKey).Result()
	if err == nil {
		log.Printf("[Cache] Exact match hit for: %s", query)
		return s.unmarshal(val)
	}

	// 语义匹配 (Semantic path)
	log.Printf("[Cache] Try semantic matching for: %s", query)
	embedding, err := s.aiClient.GenerateEmbedding(ctx, query)
	if err != nil {
		return nil, nil // 生成向量失败则降级为不走缓存
	}

	// 在 Milvus 中搜索最相似的旧查询
	searchParams, _ := entity.NewIndexHNSWSearchParam(64)
	vectors := []entity.Vector{entity.FloatVector(embedding)}

	searchResult, err := s.milvusClient.Search(
		ctx, s.collectionName, nil, "", []string{"query_hash", "query_text"},
		vectors, "embedding", entity.L2, 1, searchParams,
	)
	if err != nil || len(searchResult) == 0 || len(searchResult[0].Scores) == 0 {
		return nil, nil
	}

	score := searchResult[0].Scores[0]
	// L2 距离越小越相似
	if score <= s.threshold {
		var matchedHash string
		for _, field := range searchResult[0].Fields {
			if field.Name() == "query_hash" {
				matchedHash = field.(*entity.ColumnVarChar).Data()[0]
			}
		}

		if matchedHash != "" {
			val, err := s.redisClient.Get(ctx, matchedHash).Result()
			if err == nil {
				log.Printf("[Cache] Semantic hit! Dist: %.4f, Query: %s", score, query)
				return s.unmarshal(val)
			}
		}
	}

	return nil, nil
}

func (s *CacheService) CacheRecommendation(ctx context.Context, query string, result interface{}) error {
	hashKey := s.generateKey(query)
	data, err := json.Marshal(result)
	if err != nil {
		return err
	}

	// 1. 存入 Redis
	if err := s.redisClient.Set(ctx, hashKey, data, s.ttl).Err(); err != nil {
		return err
	}

	// 2. 将 Query 向量存入 Milvus 以便后续语义匹配
	embedding, err := s.aiClient.GenerateEmbedding(ctx, query)
	if err != nil {
		return nil
	}

	hashColumn := entity.NewColumnVarChar("query_hash", []string{hashKey})
	textColumn := entity.NewColumnVarChar("query_text", []string{query})
	vectorColumn := entity.NewColumnFloatVector("embedding", s.dimension, [][]float32{embedding})

	_, _ = s.milvusClient.Insert(ctx, s.collectionName, "", hashColumn, textColumn, vectorColumn)
	return nil
}

func (s *CacheService) generateKey(query string) string {
	hash := md5.Sum([]byte(query))
	return fmt.Sprintf("recommend:%s", hex.EncodeToString(hash[:]))
}

func (s *CacheService) unmarshal(val string) (interface{}, error) {
	var result interface{}
	if err := json.Unmarshal([]byte(val), &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *CacheService) Close() error {
	_ = s.redisClient.Close()
	return s.milvusClient.Close()
}
