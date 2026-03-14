variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["spotify-xray"]
}

target "spotify-xray" {
  dockerfile = "Dockerfile"
  tags = [
    "271122/spotify-xray:${TAG}",
    "271122/spotify-xray:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
}