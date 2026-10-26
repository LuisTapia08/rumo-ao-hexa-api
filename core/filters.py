from django_filters import rest_framework as filters
from core import models

class BaseFilter(filters.FilterSet):
    # Campo 'name' declarado aqui serve para TODOS os filtros abaixo automaticamente
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    id = filters.NumberFilter(field_name="id", lookup_expr="exact")
    is_active = filters.BooleanFilter(field_name="is_active", lookup_expr="exact")


class TeamGroupFilter(BaseFilter):
    # Removido o campo 'name' duplicado, pois ele já é herdado de BaseFilter
    class Meta:
        model = models.TeamGroup
        fields = []  # Deixe vazio ou liste apenas campos extras de busca exata


class TeamFilter(BaseFilter):
    # Removido o campo 'name' duplicado
    federation = filters.CharFilter(field_name="federation", lookup_expr="icontains", label="Federação")
    
    # Filtros de intervalo numérico para ano de fundação
    year_founded = filters.NumberFilter(field_name="year_founded", lookup_expr="exact", label="Ano exato de fundação")
    year_founded__gte = filters.NumberFilter(field_name="year_founded", lookup_expr="gte", label="Fundado após o ano")
    year_founded__lte = filters.NumberFilter(field_name="year_founded", lookup_expr="lte", label="Fundado até o ano")

    class Meta:
        model = models.Team
        fields = []


class PersonFilter(BaseFilter):
    # Filtros compartilhados por Player e Coach herdados de Person
    birth_date_gt = filters.DateFilter(field_name='birth_date', lookup_expr='gte', label='Nascido após (Data)')
    birth_date_lt = filters.DateFilter(field_name='birth_date', lookup_expr='lte', label='Nascido antes de (Data)')
    height_min = filters.NumberFilter(field_name='height', lookup_expr='gte', label='Altura mínima')
    height_max = filters.NumberFilter(field_name='height', lookup_expr='lte', label='Altura máxima')
    weight_min = filters.NumberFilter(field_name='weight', lookup_expr='gte', label='Peso mínimo')
    weight_max = filters.NumberFilter(field_name='weight', lookup_expr='lte', label='Peso máximo')
    
    # Busca exata para tamanho de camisa
    shirt_size = filters.ChoiceFilter(field_name="shirt_size", choices=models.Person.ShirtSize.choices)


class PlayerFilter(PersonFilter):
    # CORREÇÃO: Mudado de icontains para gte/lte para não quebrar o FloatField do banco
    foot_size_min = filters.NumberFilter(field_name="foot_size", lookup_expr="gte", label="Tamanho do pé mínimo")
    foot_size_max = filters.NumberFilter(field_name="foot_size", lookup_expr="lte", label="Tamanho do pé máximo")

    # Filtros de seleção para escolhas (choices) nativas do modelo
    position = filters.ChoiceFilter(field_name="position", choices=models.Player.Position.choices)
    foot_preference = filters.ChoiceFilter(field_name="foot_preference", choices=models.Player.FootPreference.choices)

    team = filters.CharFilter(field_name="team__name", lookup_expr="exact")

    class Meta:
        model = models.Player
        fields = []


class CoachFilter(PersonFilter):
    # Filtra o treinador buscando por partes do nome do seu respectivo time
    team__name = filters.CharFilter(field_name="team__name", lookup_expr="icontains", label="Nome do Time")

    class Meta:
        model = models.Coach
        fields = []
