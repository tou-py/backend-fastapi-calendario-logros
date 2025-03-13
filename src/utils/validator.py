from typing import Dict, Any


class DataValidator:
    def validate_entity_data(self, data: Dict[str, Any]) -> None:
        """
        Valida los datos de entrada para la entidad.
        Esta es una implementación base que puede ser sobrescrita por clases derivadas.

        Args:
            data: Diccionario con los datos a validar

        Raises:
            ValidationError: Si los datos no son válidos
        """
        # Implementación básica - verifica que las claves en data existan como atributos
        for key in data:
            if not hasattr(self, key):
                raise Exception(
                    f"El atributo '{key}' no existe en la entidad {self.__name__}"
                )
