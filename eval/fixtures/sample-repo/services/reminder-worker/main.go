package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	apiURL := os.Getenv("API_URL")
	if apiURL == "" {
		apiURL = "http://localhost:8000"
	}

	fmt.Printf("[ReminderWorker] Starting TaskFlow background scheduler against %s\n", apiURL)
	scheduler := NewScheduler(apiURL)
	scheduler.Start(1 * time.Minute)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	fmt.Println("[ReminderWorker] Shutting down scheduler gracefully...")
	scheduler.Stop()
}
