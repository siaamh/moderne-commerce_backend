from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_brands_subcategories_featured_discounts'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='discount',
            new_name='products_di_product_4482dd_idx',
            old_name='products_di_product_active_idx',
        ),
        migrations.RenameIndex(
            model_name='product',
            new_name='products_pr_is_acti_7d27c3_idx',
            old_name='products_pr_is_acti_feat_idx',
        ),
        migrations.RenameIndex(
            model_name='product',
            new_name='products_pr_is_acti_67ef0d_idx',
            old_name='products_pr_is_acti_brand_idx',
        ),
    ]
