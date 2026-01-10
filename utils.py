import secrets
import string

def generar_contrasena_segura(longitud=12):
    """
    Genera una contraseña segura que cumple con:
    - Al menos 8 caracteres (por defecto 12).
    - Al menos una letra mayúscula.
    - Al menos una letra minúscula.
    - Al menos un número.
    """
    # Define los conjuntos de caracteres a usar
    letras_mayusculas = string.ascii_uppercase
    letras_minusculas = string.ascii_lowercase
    digitos = string.digits
    
    # Asegura que la longitud mínima sea 8
    if longitud < 8:
        longitud = 8
        print("La longitud mínima es 8. Se ha ajustado la contraseña a 8 caracteres.")

    # 1. Garantiza que la contraseña tenga al menos un carácter de cada tipo requerido
    contrasena = [
        secrets.choice(letras_mayusculas),
        secrets.choice(letras_minusculas),
        secrets.choice(digitos)
    ]

    # 2. Llena el resto de la contraseña con una mezcla de todos los caracteres
    todos_los_caracteres = letras_mayusculas + letras_minusculas + digitos
    longitud_restante = longitud - 3
    
    for _ in range(longitud_restante):
        contrasena.append(secrets.choice(todos_los_caracteres))

    # 3. Mezcla la lista de caracteres para que no sigan un orden predecible
    secrets.SystemRandom().shuffle(contrasena)
    
    # 4. Une los caracteres para formar la cadena de texto final
    return "".join(contrasena)
