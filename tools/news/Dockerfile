FROM golang:1.25

WORKDIR /app
COPY . .

RUN go build -o news_tool news.go reddit.go google_news.go guardian.go logging.go

CMD ["./news_tool"]