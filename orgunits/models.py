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
        Реализован алгоритм поиска в ширину, создается множество посещенных узлов <children> и обьект очереди <queue>.
        Для каждого обьекта в <queue> происходит поиск детей по его id.
        Если обьект не входит во множество посещенных, он туда добавляется и попадает в очередь <queue>.
        Происходит итерация цикла со смещением по очереди, пока она не закончится.
        """
        children, queue = set(), collections.deque([root_org_id])
        children.add(root_org_id)
        
        while queue:
            # смещение очереди
            vertex = queue.popleft()
            
            new_children = Organization.objects.filter(parent_id=vertex) 
            for child in new_children:
                if child.id not in children:
                    children.add(child.id)
                    queue.append(child.id)     
        
        return self.filter(id__in=children)

    def tree_upwards(self, child_org_id):
        """
        Возвращает корневую организацию с запрашиваемым child_org_id и всех её родителей любого уровня вложенности
        Реализован алгоритм схожий с .tree_downwards(). Происходит дополнительная проверка на наличие родителей.
        Родительские обьекты не обрабатываются циклом, т. к. у экземпляра Organization может быть только один родитель. 
        """
        parents, queue = set(), collections.deque([child_org_id])
        parents.add(child_org_id)
        
        while queue:
            vertex = queue.popleft()
            instance = Organization.objects.get(id=vertex)
            
            # Проверка на наличие родителей
            try:
                parent_id = instance.parent.id
            except AttributeError:
                continue
            
            if parent_id not in parents:
                parents.add(parent_id)
                queue.append(parent_id)
        
        return self.filter(id__in=parents)


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