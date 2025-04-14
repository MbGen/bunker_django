from django.core.management.base import BaseCommand
import json
import os
from pathlib import Path
from game.models import (
    Catastrophe, Profession, HealthState, Baggage, 
    Phobia, Fact, ActionCard
)

class Command(BaseCommand):
    help = 'Загружает данные из JSON-файлов конфигурации в базу данных'

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_dir = os.path.join(base_dir, 'config')
        
        self.stdout.write(self.style.SUCCESS(f'Начинаем загрузку данных из {config_dir}'))
        
        # Загрузка катастроф
        self._load_catastrophes(os.path.join(config_dir, 'catastrophes.json'))
        
        # Загрузка профессий
        self._load_professions(os.path.join(config_dir, 'professions.json'))
        
        # Загрузка состояний здоровья
        self._load_health_states(os.path.join(config_dir, 'health_states.json'))
        
        # Загрузка багажа
        self._load_baggage(os.path.join(config_dir, 'baggage.json'))
        
        # Загрузка фобий
        self._load_phobias(os.path.join(config_dir, 'phobias.json'))
        
        # Загрузка фактов
        self._load_facts(os.path.join(config_dir, 'facts.json'))
        
        # Загрузка карт действий
        self._load_action_cards(os.path.join(config_dir, 'action_cards.json'))
        
        self.stdout.write(self.style.SUCCESS('Загрузка данных завершена успешно!'))
    
    def _load_catastrophes(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['catastrophes']:
                Catastrophe.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name'],
                        'description': item['description'],
                        'cause': item['cause'],
                        'duration_months': item['duration_months'],
                        'effects': json.dumps(item['effects'])
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["catastrophes"])} катастроф'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке катастроф: {str(e)}'))
    
    def _load_professions(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['professions']:
                Profession.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'value': item['value'],
                        'description': item['description'],
                        'category': item['category'],
                        'usefulness': item['usefulness']
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["professions"])} профессий'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке профессий: {str(e)}'))
    
    def _load_health_states(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['health_states']:
                HealthState.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'value': item['value'],
                        'description': item['description'],
                        'category': item['category'],
                        'survival_factor': item['survival_factor']
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["health_states"])} состояний здоровья'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке состояний здоровья: {str(e)}'))
    
    def _load_baggage(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['baggage']:
                Baggage.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'value': item['value'],
                        'description': item['description'],
                        'category': item['category'],
                        'usefulness': item['usefulness']
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["baggage"])} предметов багажа'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке багажа: {str(e)}'))
    
    def _load_phobias(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['phobias']:
                Phobia.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'value': item['value'],
                        'description': item['description'],
                        'category': item['category'],
                        'impact': item['impact']
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["phobias"])} фобий'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке фобий: {str(e)}'))
    
    def _load_facts(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['facts']:
                Fact.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'value': item['value'],
                        'description': item['description'],
                        'category': item['category'],
                        'usefulness': item['usefulness']
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["facts"])} фактов'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке фактов: {str(e)}'))
    
    def _load_action_cards(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data['action_cards']:
                ActionCard.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name'],
                        'description': item['description'],
                        'effect_type': item['effect_type'],
                        'effect_data': json.dumps(item['effect_data'])
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'Загружено {len(data["action_cards"])} карт действий'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при загрузке карт действий: {str(e)}'))
