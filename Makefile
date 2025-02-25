DOCKER_IMAGE_NAME := arena
DOCKER_REGISTRY := us-east4-docker.pkg.dev/hume-data/docker
DOCKER_TAG := latest

.PHONY: all
all: build tag push

.PHONY: build
build:
	@echo "Building Docker image: $(DOCKER_IMAGE_NAME)..."
	docker buildx build --no-cache --platform=linux/amd64 --load -t $(DOCKER_IMAGE_NAME) .

.PHONY: tag
tag: build
	@echo "Tagging Docker image: $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_TAG)..."
	docker tag $(DOCKER_IMAGE_NAME) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_TAG)

.PHONY: push
push: tag
	@echo "Pushing Docker image to registry: $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_TAG)..."
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_TAG)


.PHONY: clean
clean:
	@echo "Removing local Docker image: $(DOCKER_IMAGE_NAME)..."
	docker rmi $(DOCKER_IMAGE_NAME) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE_NAME):$(DOCKER_TAG) || true
