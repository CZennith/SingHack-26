/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_CONNECTOR_MODE?: string;
  readonly VITE_DATA_AS_OF?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
