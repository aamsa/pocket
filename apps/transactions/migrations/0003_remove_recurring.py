"""Remove the RecurringRule feature.

Hard-deletes every Transaction row that was generated from a recurring rule
(both past and future-dated), drops the Transaction.recurring_rule FK, then
drops the RecurringRule table itself.
"""

from django.db import migrations


def delete_rule_generated_transactions(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    Transaction.objects.filter(recurring_rule__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0002_recurringrule_transaction_recurring_rule_and_more"),
    ]

    operations = [
        migrations.RunPython(
            delete_rule_generated_transactions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="transaction",
            name="recurring_rule",
        ),
        migrations.RemoveConstraint(
            model_name="recurringrule",
            name="recurring_amount_positive",
        ),
        migrations.RemoveConstraint(
            model_name="recurringrule",
            name="recurring_interval_min1",
        ),
        migrations.RemoveConstraint(
            model_name="recurringrule",
            name="recurring_bounded",
        ),
        migrations.DeleteModel(
            name="RecurringRule",
        ),
    ]
