package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.entity.Universities;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 *
 */
@Mapper
public interface UniversityMapper {

    /**
     * 模糊查询
     * @param name
     * @return
     */
    List<Universities> query(String name);

    /**
     * ID查询
     * @param id
     * @return
     */
    @Select("select * from universities where id = #{id}")
    Universities getById(long id);

    void insert(Universities universities);

    void update(Universities universities);

    void deleteById(@Param("id") Long id);

    Page<Universities> pageQuery(@Param("name") String name, @Param("code") String code);

    @Select("select count(*) from universities")
    Integer countAll();
}
