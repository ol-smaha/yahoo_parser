from threading import Thread

from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import HttpResponse, reverse

from .models import Company


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'download_finance', 'download_news')
    search_fields = ['name']
    actions = ['run_parser']

    def get_urls(self):
        urls = super(CompanyAdmin, self).get_urls()
        custom_urls = [path('download-csv/<int:pk>/<str:category>', self.download_csv, name='download_csv')]
        return custom_urls + urls

    def download_finance(self, obj):
        if not obj.file_csv:
            return ''
        return format_html(
            '<a href="{}">Download Finance</a>',
            reverse('admin:download_csv', args=[obj.pk, 'finance'])
        )

    def download_news(self, obj):
        if not obj.file_news:
            return ''
        return format_html(
            '<a href="{}">Download News</a>',
            reverse('admin:download_csv', args=[obj.pk, 'news'])
        )

    @staticmethod
    def download_csv(request, pk, category):
        obj = Company.objects.get(pk=pk)
        filepath = obj.file_news.path if category == 'news' else obj.file_csv.path
        filename = obj.file_news if category == 'news' else obj.file_csv
        with open(filepath, 'r') as file:
            response = HttpResponse(file, content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    def run_parser(self, request, queryset):
        for obj in queryset:
            thread_csv = Thread(target=obj.download_finance_csv)
            thread_news = Thread(target=obj.download_news_csv)
            thread_csv.start()
            thread_news.start()

    run_parser.short_description = "Run parser"
    download_finance.short_description = "Finance"
    download_news.short_description = "News"


admin.site.register(Company, CompanyAdmin)
