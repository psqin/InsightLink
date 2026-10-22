/*
SQLyog Community v13.1.7 (64 bit)
MySQL - 8.1.0 : Database - insightlink01
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`insightlink01` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `insightlink01`;

/*Table structure for table `student_evaluation` */

DROP TABLE IF EXISTS `student_evaluation`;

CREATE TABLE `student_evaluation` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '点评ID',
  `material_id` bigint NOT NULL COMMENT '关联的学生材料ID',
  `score` decimal(5,2) NOT NULL COMMENT '0-100分',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '点评评语',
  `evaluation_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点评时间',
  `teacher_user_id` bigint NOT NULL COMMENT '点评导师ID',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `idx_material` (`material_id`) USING BTREE,
  KEY `teacher_user_id` (`teacher_user_id`) USING BTREE,
  CONSTRAINT `student_evaluation_ibfk_1` FOREIGN KEY (`material_id`) REFERENCES `student_material` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `student_evaluation_ibfk_2` FOREIGN KEY (`teacher_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='学生材料点评表';

/*Table structure for table `student_material` */

DROP TABLE IF EXISTS `student_material`;

CREATE TABLE `student_material` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '材料ID',
  `student_user_id` bigint NOT NULL COMMENT '学生用户ID',
  `material_type` tinyint NOT NULL COMMENT '1=学习计划 2=进度汇报 3=自我总结',
  `title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '材料标题',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '材料内容',
  `file_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '上传到OSS的文件访问地址',
  `submit_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_student_type` (`student_user_id`,`material_type`) USING BTREE,
  CONSTRAINT `student_material_ibfk_1` FOREIGN KEY (`student_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='学生材料提交表';

/*Table structure for table `students` */

DROP TABLE IF EXISTS `students`;

CREATE TABLE `students` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录唯一ID',
  `user_id` bigint NOT NULL COMMENT '关联用户ID',
  `student_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '学号',
  `university_id` bigint NOT NULL COMMENT '所属学校ID',
  `college_id` bigint DEFAULT NULL COMMENT '所属院系ID',
  `major_id` bigint DEFAULT NULL COMMENT '所属专业ID',
  `class_id` bigint DEFAULT NULL COMMENT '所属班级ID',
  `entry_year` int DEFAULT NULL COMMENT '入学年份',
  `bind_status` tinyint NOT NULL DEFAULT '0' COMMENT '绑定状态：0-未绑定导师，1-已绑定导师',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `student_no` (`student_no`) USING BTREE,
  KEY `user_id` (`user_id`) USING BTREE,
  CONSTRAINT `students_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='学生详细信息表';

/*Table structure for table `sys_dept` */

DROP TABLE IF EXISTS `sys_dept`;

CREATE TABLE `sys_dept` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '部门唯一主键',
  `NAME` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '部门名称（院系/专业/班级）',
  `dept_type` tinyint NOT NULL COMMENT '部门类型：1-院系 2-专业 3-班级',
  `parent_id` bigint DEFAULT NULL COMMENT '父级ID：院系为NULL，专业父级=院系ID，班级父级=专业ID',
  `university_id` bigint NOT NULL COMMENT '所属学校ID',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `university_id` (`university_id`) USING BTREE,
  KEY `parent_id` (`parent_id`) USING BTREE,
  CONSTRAINT `sys_dept_ibfk_1` FOREIGN KEY (`university_id`) REFERENCES `universities` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `sys_dept_ibfk_2` FOREIGN KEY (`parent_id`) REFERENCES `sys_dept` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='院系/专业/班级信息表';

/*Table structure for table `system_notice` */

DROP TABLE IF EXISTS `system_notice`;

CREATE TABLE `system_notice` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '通知ID',
  `title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '通知标题',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '通知内容',
  `publisher_id` bigint NOT NULL COMMENT '发布人用户ID',
  `publish_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
  `TYPE` tinyint NOT NULL COMMENT '1=系统通知 2=导师通知',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_publisher_type` (`publisher_id`,`TYPE`) USING BTREE,
  CONSTRAINT `system_notice_ibfk_1` FOREIGN KEY (`publisher_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='系统/导师通知表';

/*Table structure for table `teacher_student_message` */

DROP TABLE IF EXISTS `teacher_student_message`;

CREATE TABLE `teacher_student_message` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '留言ID',
  `sender_id` bigint NOT NULL COMMENT '发送人用户ID',
  `receiver_id` bigint NOT NULL COMMENT '接收人用户ID',
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '留言内容',
  `send_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `receiver_id` (`receiver_id`) USING BTREE,
  KEY `idx_sender_receiver` (`sender_id`,`receiver_id`) USING BTREE,
  CONSTRAINT `teacher_student_message_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `teacher_student_message_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='师生留言互动表';

/*Table structure for table `teachers` */

DROP TABLE IF EXISTS `teachers`;

CREATE TABLE `teachers` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录唯一ID',
  `user_id` bigint NOT NULL COMMENT '关联用户表ID',
  `teacher_no` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '工号',
  `university_id` bigint NOT NULL COMMENT '所属学校ID',
  `dept_id` bigint NOT NULL COMMENT '所属院系ID（关联sys_dept表，dept_type=1）',
  `title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '职称（教授/副教授/讲师等）',
  `research_field` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '研究领域',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `idx_user_id` (`user_id`) USING BTREE,
  UNIQUE KEY `teacher_no` (`teacher_no`) USING BTREE,
  KEY `university_id` (`university_id`) USING BTREE,
  KEY `dept_id` (`dept_id`) USING BTREE,
  CONSTRAINT `teachers_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `teachers_ibfk_2` FOREIGN KEY (`university_id`) REFERENCES `universities` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `teachers_ibfk_3` FOREIGN KEY (`dept_id`) REFERENCES `sys_dept` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='导师详细信息表';

/*Table structure for table `ts_guidance` */

DROP TABLE IF EXISTS `ts_guidance`;

CREATE TABLE `ts_guidance` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '绑定记录主键ID',
  `teacher_user_id` bigint NOT NULL COMMENT '导师的用户ID（关联user表）',
  `student_user_id` bigint NOT NULL COMMENT '学生的用户ID（关联user表）',
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `idx_student` (`student_user_id`) USING BTREE,
  KEY `teacher_user_id` (`teacher_user_id`) USING BTREE,
  CONSTRAINT `ts_guidance_ibfk_1` FOREIGN KEY (`teacher_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `ts_guidance_ibfk_2` FOREIGN KEY (`student_user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='师生指导绑定表（一对一）';

/*Table structure for table `universities` */

DROP TABLE IF EXISTS `universities`;

CREATE TABLE `universities` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '学校唯一主键',
  `NAME` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '学校名称',
  `CODE` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '学校编码（如国标码）',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='学校信息表';

/*Table structure for table `user` */

DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户唯一ID',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '登录账号',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '登录密码（MD5加密）',
  `real_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '真实姓名',
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '手机号',
  `avatar` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '头像路径',
  `role_id` int NOT NULL COMMENT '角色ID：1-管理员 2-导师 3-学生',
  `birthday` date DEFAULT NULL COMMENT '出生年月',
  `gender` tinyint DEFAULT NULL COMMENT '性别(0:保密, 1:男, 2:女)',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '联系邮箱',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `username` (`username`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=95 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC COMMENT='系统用户表';

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
