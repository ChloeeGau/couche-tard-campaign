from google.cloud import bigquery
from retail_ops.config import PROJECT_ID, BQ_DATASET, WITH_MOCKED_DATA
from retail_ops.schema import Product
from typing import List
from retail_ops.data.products import retrieve_products
class SalesTool:
    def __init__(self):
        if PROJECT_ID and not WITH_MOCKED_DATA:
            self.client = bigquery.Client(project=PROJECT_ID)
        else:
            self.client = None

    def find_low_velocity(self) -> List[Product]:
        """
        Identifies items with low sales velocity by comparing actual sales to forecasted sales.
        """
        from retail_ops.schema import CoreIdentifiers, Attributes, Categorization, CommercialStatus, Media, Description

        
        if not self.client or WITH_MOCKED_DATA:
            # Mock return for demo
            return retrieve_products()

        # Hypothetical query - comparing sales vs forecast
        # We assume there's a table with 'actual_sales' and 'forecasted_sales'
        # And we join with products to get product name if needed
        query = f"""
            SELECT 
                i.sku, i.stock_level, i.actual_sales, i.forecasted_sales,
                p.name, p.brand, p.cost, p.retail_price, p.short_description, p.long_description, p.image_uri
            FROM `{BQ_DATASET}.inventory_analysis` AS i
            JOIN `{BQ_DATASET}.products` AS p ON i.sku = p.sku
            WHERE i.actual_sales < (i.forecasted_sales * 0.6) -- 40% below forecast
            LIMIT 5
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
                        cost_price=row.get("cost"),
                        current_price=row.get("retail_price"),
                        stock_quantity=row.stock_level,
                        in_stock=True,
                        sales_velocity="Low",
                        sales_reasoning=f"Sales ({row.actual_sales}) below forecast ({row.forecasted_sales})."
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
            print(f"BigQuery Error in SalesTool: {e}")
            return []

