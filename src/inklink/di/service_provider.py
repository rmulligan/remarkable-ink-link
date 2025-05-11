"""Service provider for InkLink.

This module provides a service provider that manages dependencies and service
instantiation for the application.
"""

import logging
import importlib
from typing import Dict, Any, Type, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceProvider:
    """Service provider that manages dependencies and service instantiation."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with configuration.

        Args:
            config: Configuration dictionary
        """
        self._config = config
        self._instances = {}
        self._factories = {}

    def register(self, interface_class: Type[T], implementation_class: Type[T]) -> None:
        """
        Register an implementation class for an interface.

        Args:
            interface_class: Interface class
            implementation_class: Implementation class
        """
        if interface_class in self._factories:
            logger.warning(
                f"Overriding existing registration for {interface_class.__name__}"
            )

        # Store as a factory function
        self._factories[interface_class] = lambda: self._create_instance(
            implementation_class
        )

    def register_instance(self, interface_class: Type[T], instance: T) -> None:
        """
        Register an existing instance for an interface.

        Args:
            interface_class: Interface class
            instance: Instance to register
        """
        self._instances[interface_class] = instance

    def register_factory(self, interface_class: Type[T], factory) -> None:
        """
        Register a factory function for an interface.

        Args:
            interface_class: Interface class
            factory: Factory function that creates an instance
        """
        self._factories[interface_class] = factory

    def resolve(self, interface_class: Type[T]) -> T:
        """
        Resolve an instance for an interface.

        Args:
            interface_class: Interface class

        Returns:
            Instance of the requested interface

        Raises:
            KeyError: If the interface is not registered
        """
        # Check if instance already exists
        if interface_class in self._instances:
            return self._instances[interface_class]

        # Check if factory exists
        if interface_class in self._factories:
            # Create instance using factory
            instance = self._factories[interface_class]()
            # Cache instance for future resolves
            self._instances[interface_class] = instance
            return instance

        # If not registered, try to create instance directly
        try:
            instance = self._create_instance(interface_class)
            self._instances[interface_class] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to resolve {interface_class.__name__}: {str(e)}")
            raise KeyError(f"No registration found for {interface_class.__name__}")

    def _create_instance(self, class_type: Type[T]) -> T:
        """
        Create an instance of a class with dependencies injected.

        Args:
            class_type: Class to instantiate

        Returns:
            Instance of the class

        Raises:
            Exception: If the class cannot be instantiated
        """
        import inspect

        # Get constructor signature
        signature = inspect.signature(class_type.__init__)

        # Prepare arguments for constructor
        kwargs = {}

        # For each parameter (excluding self)
        for param_name, param in list(signature.parameters.items())[1:]:
            # If parameter has a default value and no annotation, skip
            if (
                param.default != inspect.Parameter.empty
                and param.annotation == inspect.Parameter.empty
            ):
                continue

            # If parameter is a configuration value
            if param_name in self._config:
                kwargs[param_name] = self._config[param_name]
                continue

            # If parameter has a type annotation, try to resolve it
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.resolve(param.annotation)
                    continue
                except KeyError:
                    # If we can't resolve it but it has a default value, use default
                    if param.default != inspect.Parameter.empty:
                        continue
                    # Otherwise, we can't satisfy this dependency
                    logger.error(
                        f"Cannot resolve dependency {param_name} of type {param.annotation}"
                    )
                    raise Exception(
                        f"Cannot resolve dependency {param_name} of type {param.annotation}"
                    )

            # If parameter has a default value, use it
            if param.default != inspect.Parameter.empty:
                continue

            # If we got here, we couldn't figure out how to satisfy this parameter
            logger.error(
                f"Cannot resolve parameter {param_name} for {class_type.__name__}"
            )
            raise Exception(
                f"Cannot resolve parameter {param_name} for {class_type.__name__}"
            )

        # Create instance
        return class_type(**kwargs)

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> "ServiceProvider":
        """
        Create a ServiceProvider from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured ServiceProvider
        """
        provider = ServiceProvider(config)

        # Register services from configuration if present
        services_config = config.get("SERVICES", {})

        for interface_name, implementation_name in services_config.items():
            try:
                # Dynamically import interface class
                interface_parts = interface_name.split(".")
                interface_module = importlib.import_module(
                    ".".join(interface_parts[:-1])
                )
                interface_class = getattr(interface_module, interface_parts[-1])

                # Dynamically import implementation class
                implementation_parts = implementation_name.split(".")
                implementation_module = importlib.import_module(
                    ".".join(implementation_parts[:-1])
                )
                implementation_class = getattr(
                    implementation_module, implementation_parts[-1]
                )

                # Register implementation
                provider.register(interface_class, implementation_class)

            except Exception as e:
                logger.error(
                    f"Failed to register {interface_name} -> {implementation_name}: {str(e)}"
                )

        return provider
