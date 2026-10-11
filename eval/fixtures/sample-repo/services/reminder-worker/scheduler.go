package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type OverdueTask struct {
	ID        int    `json:"id"`
	Title     string `json:"title"`
	UserEmail string `json:"user_email"`
	DueDate   string `json:"due_date"`
}

type Scheduler struct {
	apiURL     string
	httpClient *http.Client
	stopChan   chan struct{}
}

func NewScheduler(apiURL string) *Scheduler {
	return &Scheduler{
		apiURL:     apiURL,
		httpClient: &http.Client{Timeout: 10 * time.Second},
		stopChan:   make(chan struct{}),
	}
}

func (s *Scheduler) PollOverdueTasks() ([]OverdueTask, error) {
	resp, err := s.httpClient.Get(fmt.Sprintf("%s/api/v1/tasks/overdue", s.apiURL))
	if err != nil {
		return nil, fmt.Errorf("failed to fetch overdue tasks: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var tasks []OverdueTask
	if err := json.NewDecoder(resp.Body).Decode(&tasks); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return tasks, nil
}

func (s *Scheduler) Start(interval time.Duration) {
	ticker := time.NewTicker(interval)
	go func() {
		for {
			select {
			case <-ticker.C:
				tasks, err := s.PollOverdueTasks()
				if err != nil {
					fmt.Printf("[Scheduler] Error: %v\n", err)
					continue
				}
				for _, task := range tasks {
					go func(t OverdueTask) {
						fmt.Printf("[Scheduler] Alert: task '%s' (ID: %d) is overdue for %s\n", t.Title, t.ID, t.UserEmail)
					}(task)
				}
			case <-s.stopChan:
				ticker.Stop()
				return
			}
		}
	}()
}

func (s *Scheduler) Stop() {
	close(s.stopChan)
}
