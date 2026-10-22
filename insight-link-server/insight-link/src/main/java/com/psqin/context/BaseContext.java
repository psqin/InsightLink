package com.psqin.context;

import io.swagger.models.auth.In;

/**
 * ThreadLocal 一次请求，就会分配一个线程
 * ThreadLocal 存储id值
 */
public class BaseContext {

    public static ThreadLocal<Long> threadLocal = new ThreadLocal<>();
    public static ThreadLocal<Integer> threadLocal02 = new ThreadLocal<>();

    public static void setCurrentId(Long id) {
        threadLocal.set(id);
    }

    public static Long getCurrentId() {
        return threadLocal.get();
    }

    public static void removeCurrentId() {
        threadLocal.remove();
    }


    public static void setRoleId(Integer id) {
        threadLocal02.set(id);
    }

    public static Integer getRoleId() {
        return threadLocal02.get();
    }

    public static void removeRoleId() {
        threadLocal02.remove();
    }
}
