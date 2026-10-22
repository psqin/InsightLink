package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.dto.AdminTeacherSearchDTO;
import com.psqin.domain.entity.Teachers;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.psqin.domain.vo.TeacherVO;

/**
 *
 */
@Mapper
public interface TeacherMapper {

    void insert(Teachers teacher);

    Teachers getById(@Param("userId") Long userId);

    Teachers getByUserId(@Param("userId") Long userId);

    Teachers getEntityById(@Param("id") Long id);

    /**
     * 根据用户ID查询导师详细信息
     * @param userId
     * @return
     */
    TeacherVO getTeacherInfoByUserId(Long userId);

    Page<TeacherVO> pageQueryAdmin(AdminTeacherSearchDTO adminTeacherSearchDTO);

    void update(Teachers teacher);

    void deleteById(@Param("id") Long id);

    @org.apache.ibatis.annotations.Select("select count(*) from teachers")
    Integer countAll();

    @org.apache.ibatis.annotations.Select("select u.name as name, count(*) as count from teachers t join universities u on t.university_id = u.id group by t.university_id order by count desc")
    java.util.List<com.psqin.domain.vo.NameCountVO> listCountByUniversity();
}
