from rest_framework import serializers
from .models import Pojistenec

class PojistenecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pojistenec
        fields = '__all__'
        read_only_fields = ['id']  # Assuming 'id' is the primary key and should not be writable
        extra_kwargs = {
            'foto': {'required': False}  # Make foto field optional
        }
    
    def validate_foto(self, value):
        if value.size > 3 * 1024 * 1024:  # 3 MB limit
            raise serializers.ValidationError("Maximální velikost souboru je 3 MB.")
        return value
