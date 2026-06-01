declare module "swr" {
  interface SWRResponse<Data = any, Error = any> {
    data: Data | undefined;
    error: Error | undefined;
    isLoading: boolean;
    isValidating: boolean;
    mutate: (...args: any[]) => Promise<any>;
  }

  interface SWRConfiguration {
    refreshInterval?: number;
    revalidateOnFocus?: boolean;
    revalidateOnReconnect?: boolean;
    dedupingInterval?: number;
    fallbackData?: any;
    suspense?: boolean;
    fetcher?: (...args: any[]) => any;
    [key: string]: any;
  }

  export default function useSWR<Data = any, Error = any>(
    key: string | null | (() => string | null),
    fetcherOrOptions?: ((...args: any[]) => Promise<Data>) | SWRConfiguration,
    options?: SWRConfiguration
  ): SWRResponse<Data, Error>;

  export function mutate(...args: any[]): Promise<any>;
  export function useSWRConfig(): { mutate: (...args: any[]) => Promise<any>; cache: Map<string, any>; [key: string]: any };
  export function SWRConfig(props: { value: SWRConfiguration; children: React.ReactNode }): JSX.Element;
  export { SWRResponse, SWRConfiguration };
}

declare module "swr/mutation" {
  export default function useSWRMutation<Data = any, Error = any>(
    key: string,
    fetcher: (key: string, options: { arg: any }) => Promise<Data>,
    options?: any
  ): {
    data: Data | undefined;
    error: Error | undefined;
    trigger: (arg?: any) => Promise<Data>;
    isMutating: boolean;
  };
}

declare module "swr/immutable" {
  import type { SWRResponse, SWRConfiguration } from "swr";
  export default function useSWRImmutable<Data = any, Error = any>(
    key: string | null | (() => string | null),
    fetcherOrOptions?: ((...args: any[]) => Promise<Data>) | SWRConfiguration,
    options?: SWRConfiguration
  ): SWRResponse<Data, Error>;
}
