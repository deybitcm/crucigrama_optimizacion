import sys
import time

from crucigrama import Crucigrama, Variable

class CreadorCrucigrama():

    def __init__(self, crucigrama):
        """
        Crear un nuevo CSP (problema de satisfacción de restricciones) - crucigrama.
        """
        self.crucigrama = crucigrama
        self.dominios = {
            var: list(self.crucigrama.palabras.copy())
            for var in self.crucigrama.variables
        } # Dominio de cada variable

    def cuadricula_letras(self, asignacion):
        """
        Retornar una matriz (2D) representando una asignación dada.
        """
        letras = [
            [None for _ in range(self.crucigrama.ancho)]
            for _ in range(self.crucigrama.alto)
        ] # Representa la cuadricula del crucigrama con las letras asignadas a cada celda

        for variable, palabra in asignacion.items():
            direccion = variable.direccion
            for k in range(len(palabra)):
                i = variable.i + (k if direccion == Variable.ABAJO else 0)
                j = variable.j + (k if direccion == Variable.DERECHA else 0)
                letras[i][j] = palabra[k]
        return letras

    def print(self, asignacion):
        """
        Imprimir el crucigrama asignado al terminal.
        """
        letras = self.cuadricula_letras(asignacion)
        for i in range(self.crucigrama.alto):
            for j in range(self.crucigrama.ancho):
                if self.crucigrama.estructura[i][j]:
                    print(letras[i][j] or " ", end="") # Imprimir letra
                else:
                    print("█", end="")
            print() # Salto de linea

    def save(self, asignacion, filename):
        """
        Guardar el crucigrama a un archivo imagen.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letras = self.cuadricula_letras(asignacion)

        # Crear un lienzo blanco
        img = Image.new(
            "RGBA",
            (self.crucigrama.ancho * cell_size,
             self.crucigrama.alto * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crucigrama.alto):
            for j in range(self.crucigrama.ancho):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crucigrama.estructura[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letras[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letras[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letras[i][j], fill="black", font=font
                        )

        img.save(filename)

    def consistencia_nodo(self):
        """
        Actualizar `self.dominios` de forma que cada variable sea nodo-consistente.
        (Elimina cualquier valor que sea inconsistente con las restricciones unarias de una variable;
        en este caso, la longitud de la palabra).
        """

        for var in self.crucigrama.variables:
            self.dominios[var] = {
                palabra for palabra in self.dominios[var]
                if len(palabra) == var.longitud
            }

    def revisar(self, x, y):
        """
        Hacer que la variable `x` tenga consistencia de arco con la variable `y`.
        Para ello, elimine los valores de `self.dominios[x]` para los que no hay
        valor correspondiente posible para `y` en `self.dominios[y]`.

        Devuelve True si se ha hecho una revisión al dominio de `x`; devuelve
        False si no se ha hecho ninguna revisión.
        """

        # Verificar si hay solapamiento entre x y y
        solapamiento = self.crucigrama.solapamientos.get((x, y))
        if solapamiento is None:
            return False

        i, j = solapamiento
        revisado = False
        dominio_x = self.dominios[x]
        dominio_y = self.dominios[y]

        #convertir el dominio de x en una lista para poder eliminar elementos
        dominio_x = list(dominio_x)

        # Revisar cada palabra en el dominio de x
        for palabra_x in dominio_x:
            if all(palabra_x[i] == palabra_y[j] for palabra_y in dominio_y):
                continue
            dominio_x.remove(palabra_x)
            revisado = True

        return revisado

    def ac3(self, arcs=None): #Visite https://en.wikipedia.org/wiki/AC-3_algorithm para conocer la historia
        """
        Actualizar `self.dominios` de tal manera que cada variable sea consistencia de arco.
        Si `arcs` es None, comienza con la lista inicial de todos los arcos del problema.
        Si no, usa `arcs` como lista inicial de arcos para hacer consistencia.

        Devuelve True si se cumple la consistencia de arcos y no hay dominios vacíos;
        devuelve False si uno o más dominios terminan vacíos.
        """
        if arcs is None:
            arcs = list(self.crucigrama.solapamientos.keys())

        while arcs:
            x, y = arcs.pop(0)
            if self.revisar(x, y):
                if not self.dominios[x]:
                    return False
                for z in self.crucigrama.vecinos(x) - {y}:
                    arcs.append((z, x))
        return True

    def asignacion_completa(self, asignacion):
        """
        Devuelve True si `asignacion` está completa (es decir, asigna un valor a cada
        variable crucigrama); devuelve False en caso contrario.
        """
        return all(var in asignacion for var in self.crucigrama.variables)

    def consistencia(self, asignacion):
        """
        Devuelve True si `asignacion` es consistencia (es decir, las palabras encajan en crucigrama
        sin caracteres conflictivos); devuelve False en caso contrario.
        """
        #Revisar arcos (solapamientos)

        for x, y in self.crucigrama.solapamientos:
            # Si x y y están en la asignación
            if x in asignacion and y in asignacion and self.crucigrama.solapamientos[x, y] is not None:
                i, j = self.crucigrama.solapamientos[x, y]
                # Si las letras no son iguales
                if asignacion[x][i] != asignacion[y][j]:
                    return False
                
        return True # Si no hay conflictos

    def ordenar_valores_dominio(self, var, asignacion):
        """
        Devuelve una lista de valores en el dominio de `var`
        - Puede NO estar ordenada.
        - Puede estar ordenada por el número de valores que descartan para las variables vecinas (menor a mayor).
        """

        def num_eliminar(palabra):
            return sum(
                1 for vecino in self.crucigrama.vecinos(var)
                if vecino not in asignacion and palabra in self.dominios[vecino]
            )

        return sorted(self.dominios[var], key=num_eliminar)

        # return self.dominios[var]

    def seleccionar_variable_no_asignada(self, asignacion):
        """
        Devuelve una variable no asignada que no forme ya parte de `asignacion`.
        1. Puede seleccionar la siguiente variable no asignada.
        2. Puede elegir la variable con el minimo número de valores restantes en el dominio.
        3. Puede elegir la variable con el minimo número de valores restantes en el dominio; y
          si hay empate, elige la variable con el mayor grado.
        """
        
        # para 1
        # for var in self.crucigrama.variables:
        #     if var not in asignacion:
        #         return var

        # para 2
        # return min(
        #     (var for var in self.crucigrama.variables if var not in asignacion),
        #     key=lambda var: len(self.dominios[var])
        # )

        # # para 3
        return min(
            (var for var in self.crucigrama.variables if var not in asignacion),
            key=lambda var: (len(self.dominios[var]), -len(self.crucigrama.vecinos(var)))
        )

    def backtrack(self, asignacion):
        """
        Usando la Búsqueda Backtrack, toma como entrada una asignación parcial para el
        crucigrama y devuelve una asignación completa si es posible hacerlo.

        `asignacion` es un mapeo de variables (claves) a palabras (valores).

        Si no es posible la asignación, devuelve None.
        """
        
        if self.asignacion_completa(asignacion):
            return asignacion

        var = self.seleccionar_variable_no_asignada(asignacion)
        for valor in self.ordenar_valores_dominio(var, asignacion):
            asignacion[var] = valor
            if self.consistencia(asignacion):
                resultado = self.backtrack(asignacion)
                if resultado is not None:
                    return resultado
            del asignacion[var]
        return None
    
    def solve(self):
        """
        Aplique la consistencia de nodos y arcos y, a continuación, resuelva el CSP.
        """
        self.consistencia_nodo()
        if not self.ac3():
            return None
        asignacion = self.backtrack(dict())
        return asignacion

def main():

    # Verificar parametros
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py estructura palabras [output]")

    # Parseo de los argumentos
    estructura = sys.argv[1]
    palabras = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generar el crucigrama
    crucigrama = Crucigrama(estructura, palabras)
    creador = CreadorCrucigrama(crucigrama)
    # print("palabras: ", crucigrama.palabras)    
    asignacion = creador.solve()

    # Print result
    if asignacion is None:
        print("No solution.")
    else:
        creador.print(asignacion)
        if output:
            creador.save(asignacion, output)

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print("Execution time: {:.2f} seconds".format(end_time - start_time))