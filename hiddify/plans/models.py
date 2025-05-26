from django.db import models


class Plan(models.Model):
    trafic = models.IntegerField(blank=False, null=False)
    duration = models.IntegerField(blank=False, null=False, verbose_name="Duration in days")
    price = models.IntegerField(blank=False, null=False)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_datr = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'plans'
        verbose_name = 'Plan'
        verbose_name_plural = 'Plans'

    def __str__(self):
        return f"{self.trafic} گ، {self.duration} روز، {self.price} ت"
