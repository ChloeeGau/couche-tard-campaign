from app.schema import Scene

def generate_video_prompt(product_name: str, scene: Scene, product_image_uri: str, scene_image_uri: str, number_of_scenes: int=3, target_demographic: str="women age 25-35", company_name: str="Fahionista"):
  return f"""
  Generate a storyline with the following parameters:

  product_name:
  {product_name}

  target_demographic:
  {target_demographic}

  company_name:
  {company_name}

  prompt:
  {scene}

  product_image_uri:
  {product_image_uri}
  reference_images:
  ['{product_image_uri}','{scene_image_uri}']

  number_of_scenes: {number_of_scenes}
  """