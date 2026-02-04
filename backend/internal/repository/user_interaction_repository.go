package repository

import (
	"context"

	"gorm.io/gorm"

	"template-recommend/internal/models"
)

type UserInteractionRepository struct {
	db *gorm.DB
}

func NewUserInteractionRepository(db *gorm.DB) *UserInteractionRepository {
	return &UserInteractionRepository{db: db}
}

func (r *UserInteractionRepository) Create(ctx context.Context, interaction *models.UserInteraction) error {
	return r.db.WithContext(ctx).Create(interaction).Error
}

func (r *UserInteractionRepository) GetByUserID(ctx context.Context, userID string, limit int) ([]models.UserInteraction, error) {
	var interactions []models.UserInteraction
	err := r.db.WithContext(ctx).
		Where("user_id = ?", userID).
		Order("created_at DESC").
		Limit(limit).
		Find(&interactions).Error
	return interactions, err
}
