Python Classes Cheat Sheet

The self keyword:
self is a convention in Python (and a requirement in method definitions) that refers to the instance of the class. It's always the first parameter in method definitions.
Here's what self does:
1. It allows you to access the attributes and methods of the class within its own methods.
2. It helps Python distinguish between instance variables (unique to each object) and local variables within a method.


1. Class Basics
   
   Defining a Class:
   class ClassName:
       pass

   Constructor Method:
   class ClassName:
       def __init__(self, param1, param2):
           self.attribute1 = param1
           self.attribute2 = param2

   Creating an Instance:
   object_name = ClassName(arg1, arg2)

2. Class Components

   Attributes:
   - Instance attributes: self.attribute_name = value
   - Class attributes: 
     class ClassName:
         class_attribute = value

   Methods:
   class ClassName:
       def method_name(self, param1, param2):
           # Method body

   Static Methods:
   class ClassName:
       @staticmethod
       def static_method(param1, param2):
           # Method body

   Class Methods:
   class ClassName:
       @classmethod
       def class_method(cls, param1):
           # Method body

3. Inheritance

   Basic Inheritance:
   class ChildClass(ParentClass):
       pass

   Method Override:
   class ChildClass(ParentClass):
       def method_name(self, params):
           # New implementation

   Calling Parent Methods:
   class ChildClass(ParentClass):
       def method_name(self, params):
           super().method_name(params)
           # Additional code

4. Special Methods

   String Representation:
   class ClassName:
       def __str__(self):
           return "String representation"
       def __repr__(self):
           return "Detailed representation"

   Operator Overloading:
   class ClassName:
       def __add__(self, other):
           # Define addition
       def __eq__(self, other):
           # Define equality check

5. Access Modifiers

   - Public: self.attribute
   - Protected: self._attribute (convention)
   - Private: self.__attribute (name mangling)

6. Tips

   - Always use 'self' as the first parameter in instance methods
   - Use CamelCase for class names
   - Use lowercase with underscores for method and attribute names
