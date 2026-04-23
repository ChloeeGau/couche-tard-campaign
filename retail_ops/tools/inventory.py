from google.cloud import bigquery
from retail_ops.config import PROJECT_ID, BQ_DATASET, WITH_MOCKED_DATA
from retail_ops.schema import Product
from typing import List
from retail_ops.data.products import retrieve_products
class InventoryTool:
    def __init__(self):
        # Initialize client only if we have a project ID and not mocking, otherwise it might fail in dev without creds
        products_demo = None
        if PROJECT_ID and not WITH_MOCKED_DATA:
            self.client = bigquery.Client(project=PROJECT_ID)
            products_demo = retrieve_products()
        else:
            self.client = None

    def find_high_stock(self) -> List[Product]:
        """
        Identifies retail SKUs with high-stock levels using BigQuery.
        """
        from retail_ops.schema import CoreIdentifiers, Attributes, Categorization, CommercialStatus, Media, Description
        
        if not self.client or WITH_MOCKED_DATA:
            # Mock return for demo if no client/creds
            return retrieve_products()

        query = f"""
            SELECT 
                i.sku, i.stock_level, 
                p.name, p.brand, p.cost, p.retail_price, p.short_description, p.long_description, p.image_uri
            FROM `{BQ_DATASET}.inventory_analysis` AS i
            JOIN `{BQ_DATASET}.products` AS p ON i.sku = p.sku
            WHERE i.stock_level > 1000
            LIMIT 10
        """
        
        try:
            query_job = self.client.query(query)
            results = []
            for row in query_job:
                results.append(Product(
                    core_identifiers=CoreIdentifiers(
                        sku=row.sku,
                        product_name=row.name,
                        brand=row.get("brand")
                    ),
                    attributes=Attributes(),
                    categorization=Categorization(),
                    commercial_status=CommercialStatus(
                        stock_quantity=row.stock_level,
                        cost_price=row.get("cost"),
                        current_price=row.get("retail_price"),
                        in_stock=True
                    ),
                    media=Media(
                        main_image_url=row.get("image_uri")
                    ),
                    description=Description(
                        short=row.get("short_description"),
                        long=row.get("long_description")
                    )
                ))
            return results
        except Exception as e:
            print(f"BigQuery Error: {e}")
            # Fallback for demo stability
            return [
                Product(
                    core_identifiers=CoreIdentifiers(
                        sku="F-PIZZA-ERR",
                        product_name="Breakfast Pizza Slice (Fallback)"
                    ),
                    attributes=Attributes(),
                    categorization=Categorization(),
                    commercial_status=CommercialStatus(
                        stock_quantity=500,
                        in_stock=True
                    ),
                    media=Media(),
                    description=Description()
                )
            ]
