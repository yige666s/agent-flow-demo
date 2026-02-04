package models

import (
	"time"

	"github.com/lib/pq"
)

type Template struct {
	ID           int64          `gorm:"primaryKey;autoIncrement" json:"id"`
	TemplateID   string         `gorm:"uniqueIndex;size:64;not null" json:"template_id"`
	Name         string         `gorm:"size:255;not null" json:"name"`
	Description  string         `gorm:"type:text" json:"description"`
	Category     string         `gorm:"size:50;index" json:"category"`
	Tags         pq.StringArray `gorm:"type:text[];index:idx_tags,type:gin" json:"tags"`
	Style        string         `gorm:"size:50;index" json:"style"`
	ColorScheme  string         `gorm:"size:50" json:"color_scheme"`
	UseCase      string         `gorm:"size:100" json:"use_case"`
	ThumbnailURL string         `gorm:"size:512" json:"thumbnail_url"`
	PreviewURL   string         `gorm:"size:512" json:"preview_url"`
	FileURL      string         `gorm:"size:512" json:"file_url"`
	VectorID     string         `gorm:"size:64" json:"vector_id"`

	// Metadata
	CreatedAt time.Time `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
	UpdatedAt time.Time `gorm:"default:CURRENT_TIMESTAMP" json:"updated_at"`
	Status    string    `gorm:"size:20;default:'active';index" json:"status"`

	// Statistics
	ViewCount int     `gorm:"default:0" json:"view_count"`
	UseCount  int     `gorm:"default:0" json:"use_count"`
	Rating    float64 `gorm:"type:decimal(3,2)" json:"rating"`

	// Search scores (not stored in DB)
	VectorScore  float32 `gorm:"-" json:"vector_score,omitempty"`
	TagScore     float32 `gorm:"-" json:"tag_score,omitempty"`
	KeywordScore float32 `gorm:"-" json:"keyword_score,omitempty"`
	FinalScore   float64 `gorm:"-" json:"final_score,omitempty"`
}

func (Template) TableName() string {
	return "templates"
}

type UserInteraction struct {
	ID                   int64     `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID               string    `gorm:"size:64;not null;index" json:"user_id"`
	SessionID            string    `gorm:"size:64;index" json:"session_id"`
	Query                string    `gorm:"type:text;not null" json:"query"`
	Intent               string    `gorm:"type:jsonb" json:"intent"`
	RecommendedTemplates string    `gorm:"type:jsonb" json:"recommended_templates"`
	SelectedTemplateID   string    `gorm:"size:64" json:"selected_template_id"`
	Feedback             string    `gorm:"size:20" json:"feedback"` // 'positive', 'negative', 'neutral'
	ResponseTimeMs       int       `gorm:"" json:"response_time_ms"`
	CreatedAt            time.Time `gorm:"default:CURRENT_TIMESTAMP;index" json:"created_at"`
}

func (UserInteraction) TableName() string {
	return "user_interactions"
}

type User struct {
	ID          int64     `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID      string    `gorm:"uniqueIndex;size:64;not null" json:"user_id"`
	Username    string    `gorm:"size:100" json:"username"`
	Email       string    `gorm:"size:255" json:"email"`
	Preferences string    `gorm:"type:jsonb" json:"preferences"`
	CreatedAt   time.Time `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
	UpdatedAt   time.Time `gorm:"default:CURRENT_TIMESTAMP" json:"updated_at"`
}

func (User) TableName() string {
	return "users"
}

type Intent struct {
	Intent         string            `json:"intent"`
	Features       map[string]string `json:"features"`
	Keywords       []string          `json:"keywords"`
	Tags           []string          `json:"tags"`
	SearchStrategy string            `json:"search_strategy"`
}
