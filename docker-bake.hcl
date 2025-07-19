group "default" {
  targets = ["spotify-xray"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "spotify-xray" {
  dockerfile = "Dockerfile"
  tags = ["271122/spotify-xray:latest"]
}