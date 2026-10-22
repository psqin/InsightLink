package com.psqin.mapper;

import com.psqin.domain.entity.User;
import com.psqin.domain.vo.UserVO;
import com.github.pagehelper.Page;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 *
 */
@Mapper
public interface UserMapper {

    /**
     * 用户名登录
     * @param username
     * @return
     */
    @Select("select * from user where username=#{username} and role_id = #{roleId}")
    User getByUsername(String username, Integer roleId);

    /**
     * 密码登录
     * @param phone
     * @return
     */
    @Select("select * from user where phone=#{phone} and role_id = #{roleId}")
    User getByPhone(String phone, Integer roleId);

    /**
     * 新增用户
     * @param user
     */
    @Insert("insert into user (username, password, real_name, phone, avatar, role_id, birthday, gender, email) " +
            "VALUES " +
            "(#{username}, #{password}, #{realName}, #{phone}, #{avatar}, #{roleId}, #{birthday}, #{gender}, #{email})")
    void insert(User user);

    void update(User user);

    /**
     * 根据ID查询用户
     * @param id
     * @return
     */
    @Select("select * from user where id = #{id}")
    User getById(Long id);

    /**
     * 根据ID删除用户
     * @param id
     */
    @Delete("delete from user where id = #{id}")
    void deleteById(Long id);

    Page<UserVO> pageQuery(@Param("roleId") Integer roleId, @Param("keyword") String keyword, @Param("phone") String phone);

    @Select("select count(*) from user")
    Integer countAll();

    @Select("select count(*) from user where role_id = #{roleId}")
    Integer countByRole(@Param("roleId") Integer roleId);

    @Select("select date(create_time) as day, count(*) as count from user where create_time >= #{startTime} group by date(create_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCount(@Param("startTime") java.time.LocalDateTime startTime);

    @Select("select date(create_time) as day, count(*) as count from user where role_id = #{roleId} and create_time >= #{startTime} group by date(create_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCountByRole(@Param("roleId") Integer roleId, @Param("startTime") java.time.LocalDateTime startTime);
}
