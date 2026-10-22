package com.psqin.constant;

import io.swagger.models.auth.In;

/**
 * 状态常量，启用或者禁用员工
 */
public class StatusConstant {

    // 学生绑定状态
    public static final Integer STUDENT_UNBOUND = 0; // 未绑定导师
    public static final Integer STUDENT_BINDED = 1;   // 已绑定导师

    //启用
    public static final Integer ENABLE = 1;

    //禁用
    public static final Integer DISABLE = 0;

    // 健康状况编码
    public static final Integer HEALTH_GOOD      = 1; // 良好
    public static final Integer HEALTH_FAIR      = 2; // 一般
    public static final Integer HEALTH_ATTENTION = 3; // 需关注
    public static final Integer HEALTH_ILL       = 4; // 生病
    public static final Integer HEALTH_DECEASED  = 5; // 离世

    // 领养状态编码
    public static final Integer ADOPT_PENDING   = 0; // 待领养
    public static final Integer ADOPT_ADOPTED   = 1; // 已领养
    public static final Integer ADOPT_RESERVED  = 2; // 已被预定
    public static final Integer ADOPT_NULL      = 3; // 无法领养 :死亡、走失、陪伴中 的动物无法领养

    // 领养单状态常量
    public static final Integer STATUS_RESERVED = 1; // 已预定
    public static final Integer STATUS_COMPLETED = 2; // 已完成
    public static final Integer STATUS_CANCELLED = 3; // 已取消

    // 在园状态编码
    public static final Integer ON_SITE_EXITED = 0; // 已离园
    public static final Integer ON_SITE_ACTIVE = 1; // 在园

    // 离园类型编码
    public static final Integer EXIT_TYPE_NONE         = 0; // 无离园    代表没有离园
    public static final Integer EXIT_TYPE_ADOPTED      = 1; // 领养
    public static final Integer EXIT_TYPE_DECEASED     = 2; // 死亡
    public static final Integer EXIT_TYPE_LOST         = 3; // 走失
    public static final Integer EXIT_TYPE_HOME_COMPANY = 4; // 陪伴到家

    //服务类型
    public static final Integer SERVICE_INSTORE   = 1; //陪伴在店
    public static final Integer SERVICE_HOME     = 2; //陪伴到家

    //陪伴状态
    public static final Integer CONTINUE         = 1; //进行中
    public static final Integer COMPLETE         = 2; //完成
    public static final Integer CANCLE           = 3; //取消


}
