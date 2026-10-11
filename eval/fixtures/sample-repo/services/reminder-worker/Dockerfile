FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod ./
COPY *.go ./
RUN go build -o reminder-worker .

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/reminder-worker .
CMD ["./reminder-worker"]
