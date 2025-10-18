class DIContainer:
    """Simple dependency injection container."""
    
    _instance = None
    _dependencies = {}
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern to get the container instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, key, implementation):
        """Register an implementation for a key."""
        self._dependencies[key] = implementation
    
    def resolve(self, key):
        """Resolve an implementation for a key."""
        if key not in self._dependencies:
            raise KeyError(f"No implementation registered for {key}")
        
        implementation = self._dependencies[key]
        
        # If it's a factory function that requires the container
        if callable(implementation) and not isinstance(implementation, type):
            return implementation(self)
        
        # If the registered item is a class, instantiate it
        elif isinstance(implementation, type):
            return implementation()
        
        return implementation
