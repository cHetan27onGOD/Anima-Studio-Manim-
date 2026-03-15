FROM manimcommunity/manim:v0.19.2

WORKDIR /manim

# Install additional dependencies if needed
RUN pip install --no-cache-dir --upgrade pip

# Create outputs directory
RUN mkdir -p /manim/outputs

# Keep container running
CMD ["tail", "-f", "/dev/null"]
