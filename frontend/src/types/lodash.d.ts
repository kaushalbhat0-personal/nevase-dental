/* eslint-disable @typescript-eslint/no-explicit-any -- minimal typings for untyped CJS module */
declare module 'lodash.debounce' {
  interface DebouncedFunc<T extends (...args: any[]) => any> {
    (...args: Parameters<T>): ReturnType<T> | undefined;
    cancel(): void;
    flush(): ReturnType<T> | undefined;
  }

  function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait?: number,
    options?: {
      leading?: boolean;
      trailing?: boolean;
      maxWait?: number;
    }
  ): DebouncedFunc<T>;

  export default debounce;
}
