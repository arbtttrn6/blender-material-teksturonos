bl_info = {
    "name": "Teksturonos",
    "author": "arbtttrn6",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "Properties > Material > Teksturonos",
    "description": "Для разного вытащенного с помощью UmodelViewer-а. По имени материалов на моделях ищет соответствующие mat-файлы для получения из них диффузных текстур и текстур нормалей.",
    "category": "Material",
}

import bpy
import os
from pathlib import Path

class MATERIAL_OT_import_texture(bpy.types.Operator):
    """Импорт текстуры из материала"""
    bl_idname = "material.import_texture"
    bl_label = "Импорт текстур"
    bl_options = {'REGISTER', 'UNDO'}
    
    models_path: bpy.props.StringProperty(
        name="Путь к материалам",
        description="Путь до папки с материалами",
        subtype='DIR_PATH',
        default=""
    )
    
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.active_material is not None
    
    def execute(self, context):
        if not self.models_path:
            self.report({'ERROR'}, "Укажите путь к материалам")
            return {'CANCELLED'}
        
        # Получаем абсолютный путь
        absolute_path = self.resolve_path(context, self.models_path)
        models_root = Path(absolute_path)
        
        self.report({'INFO'}, f"Поиск в: {models_root}")
        
        if not models_root.exists():
            self.report({'ERROR'}, f"Такого пути нема: {models_root}")
            return {'CANCELLED'}
        
        obj = context.object
        
        success_count = 0
        fail_count = 0
        
        # Process each material slot of the active object
        for material_slot in obj.material_slots:
            material = material_slot.material
            if not material:
                continue
                
            material_name = material.name
            self.report({'INFO'}, f"Обработка материала: {material_name}")
            
            # Поиск файла, описывающего материал
            txt_file = self.find_material_txt_file(models_root, material_name)
            
            if not txt_file:
                self.report({'WARNING'}, f"Неуспешен поиск материала для: {material_name}")
                fail_count += 1
                continue
            
            # Чтение параметра цветовой текстуры
            diffuse_texture_name = self.read_diffuse_from_txt(txt_file)
            
            # Чтение параметра карты нормалей
            normal_texture_name = self.read_normal_from_txt(txt_file)
            
            # Чтение параметра текстуры отражений
            specular_texture_name = self.read_specular_from_txt(txt_file)
            
            diffuse_path = None
            
            if diffuse_texture_name:
                diffuse_path = self.find_texture_file(models_root, diffuse_texture_name)
                if not diffuse_path:
                    self.report({'WARNING'}, f"Неуспешен поиск текстуры: {diffuse_texture_name}")
             
            normal_path = None
             
            if normal_texture_name:
                 normal_path = self.find_texture_file(models_root, normal_texture_name)
                 if not normal_path:
                    self.report({'WARNING'}, f"Неуспешен поиск текстуры: {normal_texture_name}")
            
            specular_path = None
            
            if specular_texture_name:
                specular_path = self.find_texture_file(models_root, specular_texture_name)
                if not specular_path:
                    self.report({'WARNING'}, f"Неуспешен поиск текстуры: {specular_texture_name}")
            
            # Текстуры к материалу
            if self.assign_textures_to_material(material, diffuse_path, normal_path, specular_path):
                success_count += 1
                self.report({'INFO'}, f"Успешно добавление текстур к {material_name}")
            else:
                fail_count += 1
        
        self.report({'INFO'}, f"Готово: {success_count} успешно, {fail_count} неуспешно")
        return {'FINISHED'}
    
    def find_material_txt_file(self, root_path, material_name):
        """Поиск mat файла с именем по имени материала объекта"""
        for root, dirs, files in os.walk(root_path):
            for file in files:
                if file.lower() == f"{material_name.lower()}.mat":
                    return Path(root) / file
                
                # Проверка без расширения
                if file.lower().endswith('.mat') and file[:-4].lower() == material_name.lower():
                    return Path(root) / file
        return None
    
    def resolve_path(self, context, path):
        """Конвертование относительного пути в абсолютный"""
        if not path:
            return path
            
        # Если путь уже абсолютный --> возврат что есть
        if os.path.isabs(path):
            return path
            
        # Получение доступа к положению blend-файла
        blend_filepath = context.blend_data.filepath
        if blend_filepath:
            # Путь к папке .blend файла
            blend_dir = os.path.dirname(blend_filepath)
            # Совмещение с относительным путем
            absolute_path = os.path.normpath(os.path.join(blend_dir, path))
            return absolute_path
        else:
            # Если файл не сохранен --> возврат исходного пути
            self.report({'WARNING'}, "Blend-файл не сохранен. Использование пути как есть.")
            return path
    
    def find_material_txt_file(self, root_path, material_name):
        """Поиск mat-файла по имени материала"""
        for root, dirs, files in os.walk(root_path):
            for file in files:
                if file.lower() == f"{material_name.lower()}.mat":
                    return Path(root) / file
                
                # На всякий случай поиск без расширения
                if file.lower().endswith('.mat') and file[:-4].lower() == material_name.lower():
                    return Path(root) / file
        return None
    
    def read_diffuse_from_txt(self, txt_file_path):
        """Чтение параметра диффузной текстуры из mat-файла"""
        try:
            with open(txt_file_path, 'r') as file:
                for line in file:
                    if line.strip().startswith('Diffuse='):
                        diffuse_value = line.strip().split('=', 1)[1].strip()
                        if diffuse_value:
                            return diffuse_value
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка при чтении {txt_file_path}: {str(e)}")
        return None
    
    def read_normal_from_txt(self, txt_file_path):
        """Чтение параметра текстуры нормалей из mat-файла"""
        try:
            with open(txt_file_path, 'r') as file:
                for line in file:
                    if line.strip().startswith('Normal='):
                        normal_value = line.strip().split('=', 1)[1].strip()
                        if normal_value:
                            return normal_value
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка при чтении {txt_file_path}: {str(e)}")
        return None
    
    def read_specular_from_txt(self, txt_file_path):
        """Чтение параметра текстуры отражений из mat-файла"""
        try:
            with open(txt_file_path, 'r') as file:
                for line in file:
                    if line.strip().startswith('Specular='):
                        specular_value = line.strip().split('=', 1)[1].strip()
                        if specular_value:
                            return specular_value
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка при чтении {txt_file_path}: {str(e)}")
        return None
    
    def find_texture_file(self, root_path, texture_name):
        """Поиск файла текстуры по имени"""
        # Добавить или изменить формат в зависимости от нужного формата текстуры
        image_extensions = {'.png', '.jpg', '.jpeg', '.tga', '.dds'}
        
        # В начале попробовать найти имя с разными расширениями
        for ext in image_extensions:
            potential_path = root_path / f"{texture_name}{ext}"
            if potential_path.exists():
                return potential_path
        
        # Если не нашли --> рекурсивный поиск
        for root, dirs, files in os.walk(root_path):
            for file in files:
                file_lower = file.lower()
                name_without_ext = Path(file).stem.lower()
                
                if name_without_ext == texture_name.lower():
                    file_ext = Path(file).suffix.lower()
                    if file_ext in image_extensions:
                        return Path(root) / file
                    
        return None
    
    def assign_textures_to_material(self, material, diffuse_path, normal_path, specular_path):
        """Соединение текстур к узлам материала"""
        try:
            # Включение использования материалом узлов-нод
            material.use_nodes = True
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            
            # Получаем или создаем Principled BSDF
            principled_node = None
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                    break
            
            if not principled_node:
                principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
                principled_node.location = (0, 300)
                
                # Соединение с выходом материала
                output_node = None
                for node in nodes:
                    if node.type == 'OUTPUT_MATERIAL':
                        output_node = node
                        break
                
                if not output_node:
                    output_node = nodes.new(type='ShaderNodeOutputMaterial')
                    output_node.location = (300, 300)
                
                links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
            
            # Обработка диффузной текстуры
            if diffuse_path:
                # Поиск или создание узла Diffuse текстуры
                diffuse_node = None
                for node in nodes:
                    if node.type == 'TEX_IMAGE' and node.label == 'Diffuse':
                        diffuse_node = node
                        break
                
                if not diffuse_node:
                    diffuse_node = nodes.new(type='ShaderNodeTexImage')
                    diffuse_node.label = 'Diffuse'
                    diffuse_node.location = (-300, 300)
                
                # Загрузка изображения для диффузной текстуры
                diffuse_img = self.load_image(str(diffuse_path))
                if diffuse_img:
                    diffuse_node.image = diffuse_img
                    # Соединение изображения с базовым цветом
                    if not any(link.from_node == diffuse_node for link in links):
                            links.new(diffuse_node.outputs['Color'], principled_node.inputs['Base Color'])
            
            # Обработка текстуры нормалей
            if normal_path:
                # Поиск или создание узла Normal текстуры
                normal_node = None
                for node in nodes:
                    if node.type == 'TEX_IMAGE' and node.label == 'Normal':
                        normal_node = node
                        break
                
                if not normal_node:
                    normal_node = nodes.new(type='ShaderNodeTexImage')
                    normal_node.label = 'Normal'
                    normal_node.location = (-450, -300)
                
                # Загрузка изображения для текстуры нормалей
                normal_img = self.load_image(str(normal_path))
                if normal_img:
                    normal_node.image = normal_img
                    
                    normal_node.image.colorspace_settings.name = 'Non-Color'
                    
                    # Поиск или создание узла Normal Map
                    normal_map_node = None
                    for node in nodes:
                        if node.type == 'NORMAL_MAP':
                            normal_map_node = node
                            break
                    
                    if not normal_map_node:
                        normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                        normal_map_node.location = (-180, -300)
                        normal_map_node.space = 'TANGENT'
                    
                    # Соединение текстуры с Normal Map
                    if not any(link.from_node == normal_node for link in links):
                        links.new(normal_node.outputs['Color'], normal_map_node.inputs['Color'])
                    
                    # Соединение Normal Map с Principled BSDF
                    if not any(link.to_node == principled_node and link.to_socket == 'Normal' for link in links):
                        links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            
            # Обработка текстуры отражений
            if specular_path:
                # Поиск или создание узла Specular текстуры
                specular_node = None
                for node in nodes:
                    if node.type == 'TEX_IMAGE' and node.label == 'Specular':
                        specular_node = node
                        break
                
                if not specular_node:
                    specular_node = nodes.new(type='ShaderNodeTexImage')
                    specular_node.label = 'Specular'
                    specular_node.location = (-300, 0)
                
                # Загрузка изображения для текстуры отражений
                specular_img = self.load_image(str(specular_path))
                if specular_img:
                    specular_node.image = specular_img
                    specular_node.image.colorspace_settings.name = 'Non-Color'
                    
                    if not any(link.from_node == specular_node for link in links):
                        if bpy.app.version < (4, 0, 0):
                            links.new(specular_node.outputs['Color'], principled_node.inputs['Specular'])
                        else:
                            links.new(specular_node.outputs['Color'], principled_node.inputs['Specular IOR Level'])
            
            return True
            
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка добавления текстур к {material.name}: {str(e)}")
            return False
    
    def load_image(self, image_path):
        """Загрузка изображения в Blender"""
        try:
            # Проверяем, загружено ли уже изображение
            for img in bpy.data.images:
                if img.filepath == image_path:
                    return img
            
            # Загружаем новое изображение
            img = bpy.data.images.load(image_path)
            return img
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка загрузки изображения {image_path}: {str(e)}")
            return None

class MATERIAL_PT_texture_importer(bpy.types.Panel):
    """Панель для текстуроноса в настройках материала"""
    bl_label = "Teksturonos"
    bl_idname = "MATERIAL_PT_texture_importer"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.material is not None
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        layout.label(text="Импорт текстур по материалам", icon='TEXTURE')
        layout.separator()
        
        # Create a property for storing the path
        scene = context.scene
        if not hasattr(scene, "texture_importer_path"):
            scene.texture_importer_path = ""
        
        layout.prop(scene, "texture_importer_path", text="Путь к текстурам")
        layout.separator()
        
        # Button to process all materials of active object
        if obj and obj.active_material:
            row = layout.row(align=True)
            op = row.operator("material.import_texture", text="Найти все текстуры", icon='IMPORT')
            op.models_path = scene.texture_importer_path
            
            if scene.texture_importer_path:
                box = layout.box()
                box.label(text="Текущий путь:", icon='INFO')
                box.label(text=f"  {scene.texture_importer_path}")
                
                # Показываем абсолютный путь
                abs_path = resolve_path_static(context, scene.texture_importer_path)
                if abs_path != scene.texture_importer_path:
                    box.label(text="Абсолютный путь:")
                    box.label(text=f"  {abs_path}")
        else:
            layout.label(text="Нема активного материала", icon='ERROR')

def resolve_path_static(context, path):
    if not path:
        return path
        
    if os.path.isabs(path):
        return path
        
    blend_filepath = context.blend_data.filepath
    if blend_filepath:
        blend_dir = os.path.dirname(blend_filepath)
        absolute_path = os.path.normpath(os.path.join(blend_dir, path))
        return absolute_path
    else:
        return path

# Регистрация параметров
def register_properties():
    bpy.types.Scene.texture_importer_path = bpy.props.StringProperty(
        name="Models Path",
        description="Путь к основной папке с материалами и текстурами",
        subtype='DIR_PATH',
        default=""
    )

def unregister_properties():
    del bpy.types.Scene.texture_importer_path


# Регистрация дела
classes = [MATERIAL_OT_import_texture, MATERIAL_PT_texture_importer]

def register():
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_properties()


if __name__ == "__main__":
    register()
