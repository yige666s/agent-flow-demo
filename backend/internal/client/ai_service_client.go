package client

import (
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"template-recommend/internal/models"
	pb "template-recommend/proto"
)

type AIServiceClient struct {
	conn   *grpc.ClientConn
	client pb.AIServiceClient
}

func NewAIServiceClient(addr string) (*AIServiceClient, error) {
	// TODO: Add retry and timeout configuration
	conn, err := grpc.Dial(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(10*1024*1024)),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to AI service: %w", err)
	}

	return &AIServiceClient{
		conn:   conn,
		client: pb.NewAIServiceClient(conn),
	}, nil
}

func (c *AIServiceClient) UnderstandIntent(
	ctx context.Context,
	query string,
	userID string,
) (*models.Intent, error) {
	req := &pb.IntentRequest{
		Query:  query,
		UserId: userID,
	}

	resp, err := c.client.UnderstandIntent(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("understand intent failed: %w", err)
	}

	return &models.Intent{
		Intent:         resp.Intent,
		Features:       resp.Features,
		Keywords:       resp.Keywords,
		Tags:           resp.Tags,
		SearchStrategy: resp.SearchStrategy,
	}, nil
}

func (c *AIServiceClient) GenerateEmbedding(
	ctx context.Context,
	text string,
) ([]float32, error) {
	req := &pb.EmbeddingRequest{
		Text: text,
	}

	resp, err := c.client.GenerateEmbedding(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("generate embedding failed: %w", err)
	}

	return resp.Embedding, nil
}

func (c *AIServiceClient) GenerateExplanation(
	ctx context.Context,
	query string,
	templates []models.Template,
) (string, error) {
	var pbTemplates []*pb.Template
	for _, tmpl := range templates {
		pbTemplates = append(pbTemplates, &pb.Template{
			TemplateId:  tmpl.TemplateID,
			Name:        tmpl.Name,
			Description: tmpl.Description,
			Tags:        tmpl.Tags,
		})
	}

	req := &pb.ExplanationRequest{
		Query:     query,
		Templates: pbTemplates,
	}

	resp, err := c.client.GenerateExplanation(ctx, req)
	if err != nil {
		return "", fmt.Errorf("generate explanation failed: %w", err)
	}

	return resp.Explanation, nil
}

func (c *AIServiceClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}
