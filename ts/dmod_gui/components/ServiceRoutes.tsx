import React, {
    Context,
    createContext,
    Dispatch,
    ReactNode,
    SetStateAction,
    useContext,
    useEffect,
    useState
} from "react";
import {SERVICE_ROUTE_FILEPATH, ServiceName} from "../utils/constants";
import rawRoutes from "../public/service_routes.json";

const routes = rawRoutes as Record<ServiceName, ServiceRoute>;

/**
 * Basic interface used to describe the basic building blocks used to describe a route to a service
 */
export interface ServiceRoute {
    identifier: string
    address?: string
    path?: string
    port?: number
}

/**
 * Represents a mapping from an identifiable name to the route that belongs to it
 */
export type ServiceRoutes = Record<string, ServiceRoute>

/**
 * Defines the required signature used for a function that will load service routes
 *
 * @param setter The setX function used to store the loaded data
 * @param options Any additional values that might be needed to load values
 */
export type ServiceRouteLoader = (setter: Dispatch<SetStateAction<ServiceRoutes>>, options?: object) => void;

/**
 * The default load logic for service routes
 * @param storeRoutes The function used to store route data
 */
export function DefaultServiceRouteLoader(storeRoutes: Dispatch<SetStateAction<ServiceRoutes>>) {
    console.log(`Looking for service routes at ${SERVICE_ROUTE_FILEPATH}`);
    fetch(SERVICE_ROUTE_FILEPATH).then(
        (value: globalThis.Response): Record<string, any> => {
            if (value.ok) {
                return value.json();
            }
            throw value;
        }
    ).then((routeData) => {
        storeRoutes(routeData);
    })
}

/**
 * Provide access to service route information
 *
 * @param loader Backend logic used to read route data
 * @param options Options that may be needed for the loader
 */
export function useServiceRouteLoader(loader?: ServiceRouteLoader, options?: object): ServiceRoutes {
    if (typeof loader === 'undefined' || loader === null) {
        loader = DefaultServiceRouteLoader;
    }
    const [routes, setRoutes] = useState<ServiceRoutes>({});
    
    useEffect(() => {
        console.log("Loading routes");
        if(loader) {
            loader(setRoutes, options);
        }
    }, [loader, options, routes])
    
    return routes;
}

/**
 * Represents the basic parameters used to load service routes
 */
export interface ServiceRouteProviderProperties {
    loader?: ServiceRouteLoader,
    options?: Record<string, any>
    children?: ReactNode | undefined;
}

/**
 * A common context for service route information
 */
const ServiceRouteContext: Context<ServiceRoutes> = createContext({});

/**
 * A component that sets up access to service routes to its children
 * @param properties The values required to load service routes
 */
export function ServiceRouteProvider(
    properties: ServiceRouteProviderProperties
): JSX.Element {
    const {loader, options} = properties;
    const routes = useServiceRouteLoader(loader, options);
    
    return (
        <ServiceRouteContext.Provider value={routes}>
            { properties.children }
        </ServiceRouteContext.Provider>
    );
}

export function useServiceAddress(serviceName: ServiceName): string {
    if (!Object.hasOwn(routes, serviceName)) {
        throw new Error(`There is no route to a service identified as ${serviceName}`);
    }
    
    const route = routes[serviceName];
    
    return convertRouteToAddress(route);
}

/**
 * Take a route object and convert it to a string that can be used in HTTP communication
 * @param route
 */
export function convertRouteToAddress(route: ServiceRoute): string {
    if (!route.address && !route.port) {
        throw new Error(
            `Cannot form an address for the ${route.identifier} service - a port must be provided if an address isn't`
        );
    }
    
    let address = route.address || "http://127.0.0.1"
    address = address.replace(/\/$/, '')
    
    if (route.port) {
        address += `:${route.port}`;
    }
    
    if (route.path) {
        let path = route.path.replace(/^\//, '')
        address = `${address}/${path}`;
    }
    
    return address;
}

/**
 * Hook to allow easy access to the service route context data
 */
export function useServiceRoutes() {
    return useContext<ServiceRoutes>(ServiceRouteContext);
}

export default ServiceRouteProvider;