package com.psqin.utils;

import java.security.SecureRandom;
import java.util.Random;

/**
 * NanoId生成工具类
 */
public class NanoIdUtils {

    /**
     * 默认使用的字符集（64个字符）
     */
    private static final char[] ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz-".toCharArray();

    private static final SecureRandom RANDOM = new SecureRandom();

    /**
     * 生成指定长度的NanoId
     * @param size 长度
     * @return NanoId字符串
     */
    public static String randomNanoId(int size) {
        if (size <= 0) {
            throw new IllegalArgumentException("size must be greater than 0");
        }
        
        StringBuilder sb = new StringBuilder(size);
        for (int i = 0; i < size; i++) {
            sb.append(ALPHABET[RANDOM.nextInt(ALPHABET.length)]);
        }
        return sb.toString();
    }
}
