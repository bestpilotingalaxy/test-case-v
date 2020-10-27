"""
Copyright 2020 ООО «Верме»
"""
import collections

from django.db import models
from django.db.models.expressions import RawSQL


class OrganizationQuerySet(models.QuerySet):
    def tree_downwards(self, root_org_id):
        """
        Возвращает корневую организацию с запрашиваемым root_org_id и всех её детей любого уровня вложенности.
        Рекурсивный запрос с помощью RaqSQL, в рамках тестов на оптимизацию.
        """
        raw_query = RawSQL(
            """
            WITH RECURSIVE children AS (
                
                SELECT id
                FROM orgunits_organization
                WHERE id = %s
              
              UNION ALL
                
                SELECT o.id
                FROM orgunits_organization  o, children  c
                WHERE o.parent_id = c.id
            )
            SELECT id FROM children
            """,
            [root_org_id]
        )
        return self.filter(id__in=raw_query)

    def tree_upwards(self, child_org_id):
        """
        Возвращает корневую организацию с запрашиваемым child_org_id и всех её родителей любого уровня вложенности.
        Рекурсивный запрос с помощью RaqSQL, в рамках тестов на оптимизацию.
        """
        raw_query = RawSQL(
            """
            WITH RECURSIVE parents AS (
                
                SELECT id, parent_id
                FROM orgunits_organization
                WHERE id = %s
              
              UNION ALL
                
                SELECT o.id, o.parent_id
                FROM orgunits_organization  o, parents  p
                WHERE o.id = p.parent_id
            )
            SELECT id FROM parents
            """,
            [child_org_id]
        )
        return self.filter(id__in=raw_query)


class Organization(models.Model):
    """ Организаци """

    objects = OrganizationQuerySet.as_manager()

    name = models.CharField(max_length=1000, blank=False, null=False, verbose_name="Название")
    code = models.CharField(max_length=1000, blank=False, null=False, unique=True, verbose_name="Код")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, verbose_name="Вышестоящая организация",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Организация"
        verbose_name = "Организации"

    def parents(self):
        """
        Возвращает всех родителей любого уровня вложенности
        Применение .tree_upwards() с последующим исключением собственного экземпляра.
        """
        parents = type(self).objects.tree_upwards(self.id).exclude(id=self.id)
        return parents

    def children(self):
        """
        Возвращает всех детей любого уровня вложенности
        Применение .tree_downeards() с последующим исключением собственного экземпляра.
        """
        children = type(self).objects.tree_downwards(self.id).exclude(id=self.id)
        return children
    
    def __str__(self):
        return self.name