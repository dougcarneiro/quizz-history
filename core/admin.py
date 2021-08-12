from django.contrib import admin
from django.forms import ModelForm, ModelMultipleChoiceField
from simple_history.admin import SimpleHistoryAdmin
from .models import *

# Register your models here.
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0

class QuestionAdmin(SimpleHistoryAdmin):
    inlines = [
        AnswerInline,
    ]

admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, SimpleHistoryAdmin)

admin.site.register(Match, SimpleHistoryAdmin)
admin.site.register(Team, SimpleHistoryAdmin)