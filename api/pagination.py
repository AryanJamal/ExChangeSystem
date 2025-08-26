from rest_framework.pagination import PageNumberPagination


class TenPerPagePagination(PageNumberPagination):
    page_size = 30  # same as SALES_PER_PAGE on the front‑end
    page_size_query_param = "page_size"
    max_page_size = 300
