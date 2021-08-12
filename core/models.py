from django.db import models
from simple_history.models import HistoricalRecords

# Create your models here.
class Question(models.Model):
    STYLE_CHOICES = (
        ('N', 'Normal'),
        ('C', 'Challenge'),
    )

    history = HistoricalRecords()

    title = models.TextField(default='')
    style = models.CharField(max_length=1, choices=STYLE_CHOICES)

    def __str__(self):
       return self.title

class Answer(models.Model):
    history = HistoricalRecords()

    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.TextField(default='')
    is_correct = models.BooleanField(default=False)

    def __str__(self):
       return self.content

class Match(models.Model):
    dateTime = models.DateTimeField(auto_now=True)
    shift = models.IntegerField(default=0)

    def __str__(self):
       return self.dateTime.strftime('%d/%m/%Y %H:%M:%S')

class Team(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    name = models.CharField(max_length=40, default='')
    points = models.IntegerField(default=0)

    def __str__(self):
       return self.name

class MatchQuestion(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True)
    shift = models.IntegerField(default=0)
    right_answer = models.BooleanField(blank=True, null=True)
