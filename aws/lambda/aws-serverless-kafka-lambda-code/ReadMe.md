# 1. Create layer package
mkdir -p python
pip install -r requirements.txt -t python/
zip -r9 msk_dependencies_layer.zip python

# 2. Upload as layer in AWS Console
# 3. Attach layer to your function
# 4. Now your function ZIP only needs your code files