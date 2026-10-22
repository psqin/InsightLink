package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.entity.SysDept;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 *
 */
@Mapper
public interface SysDeptMapper {

    /**
     * 校验学校、学院、专业、班级的层级关系是否正确
     * @param universityId
     * @param collegeId
     * @param majorId
     * @param classId
     * @return
     */
    Integer countValidHierarchy(@Param("universityId") Long universityId,
                                @Param("collegeId") Long collegeId,
                                @Param("majorId") Long majorId,
                                @Param("classId") Long classId);

    /**
     * 根据学校ID查询院系列表（dept_type=1）
     */
    java.util.List<SysDept> listCollegesByUniversityId(@Param("universityId") Long universityId);

    /**
     * 根据院系ID查询专业列表（dept_type=2）
     */
    java.util.List<SysDept> listMajorsByCollegeId(@Param("collegeId") Long collegeId);

    /**
     * 根据专业ID查询班级列表（dept_type=3）
     */
    java.util.List<SysDept> listClassesByMajorId(@Param("majorId") Long majorId);

    SysDept getById(@Param("id") Long id);

    void insert(SysDept sysDept);

    void update(SysDept sysDept);

    void deleteById(@Param("id") Long id);

    Integer countByParentId(@Param("parentId") Long parentId);

    Page<SysDept> pageQuery(@Param("universityId") Long universityId,
                            @Param("deptType") Integer deptType,
                            @Param("parentId") Long parentId,
                            @Param("name") String name);

    @org.apache.ibatis.annotations.Select("select count(*) from sys_dept where dept_type = #{deptType}")
    Integer countByDeptType(@Param("deptType") Integer deptType);
}
